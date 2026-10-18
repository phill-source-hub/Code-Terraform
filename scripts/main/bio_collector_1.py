"""Bio Collector: collect the fragments open Bio Orders still need, otherwise explore.

Where it runs: machine script slot `bio_collector_1` (self = this collector).
Self-contained on purpose (ADR-014): no imports.
Each pass re-reads the world and remembers nothing, so a restart or game load resumes from
    what the machines hold. One specimen at a time: nothing is collected while the cargo slot
    is occupied.
Target choice, in order:
    1. A cataloged location whose fragment still has units missing. Units missing are worked
       out per fragment for each open Bio Order in this outpost's biome:
           requires - delivered - in_transit - in Inventory - specimens already in flight
       The largest shortfall across the orders is used, so one fragment is never counted twice.
    2. Otherwise explore: the nearest unknown location, so the Bio Lab can identify it. This
       runs only while some fragment type of this biome is not yet in the Journal. An unknown
       dot can turn out to be a type already cataloged elsewhere, so exploring after every type
       is known only wastes trips. Orders still come first (step 1).
    3. Otherwise idle and recheck later.
Why not "first required fragment": the old script kept collecting the first required fragment
    after it was cataloged, because it never subtracted what the order already had.
Waiting: collect() is timed and pauses this script, so the loop sleeps only when idle or blocked.
Assumption (UNVERIFIED, docs/api-notes.md): another script can read bio_lab_1.specimen. If that
    read fails, the Lab chamber is not counted and the Lab may get one specimen more than needed.
API facts relied on (docs/game/biology.md): self.scan(), self.collect(coords), self.cargo,
    self.outpost.biome, FragmentLocation .coords .distance .cataloged .fragment_id,
    Specimen .coords .fragment_id, BioOrder .id .biome .status .requires .delivered .in_transit,
    bio_exchange.orders(), inventory.count(item_id), journal.cataloged_fragments(planet_id),
    get_component, set_status, print, sleep.
"""

PAUSE_SECONDS = 60
RETRY_SECONDS = 5
EXCHANGE_ID = "bio_exchange_1"
LAB_ID = "bio_lab_1"
JOURNAL_ID = "journal"
# Journal planet id; the manual says the current planet is usually "nocturna".
PLANET_ID = "nocturna"

# Every fragment type per biome, from the manual's Biology Samples page (241). Used only to
# decide whether exploring can still find something new.
BIOME_FRAGMENTS = {
    "frozen": [
        "gw_cranial_plate",
        "vc_dorsal_carapace",
        "oc_cranium",
        "bw_skull",
        "vd_bell",
        "mh_fruiting_body",
        "hs_mandible",
        "ms_chelicera",
        "hc_aperture_lip",
        "ma_cranial_papilla",
        "gm_compound_eye",
        "fs_calyx_plate",
        "sd_cranial_crest",
        "ce_stalked_eye",
        "st_scute_plate",
        "vm_cephalic_horn",
    ],
    "coastal": [
        "gw_caudal_fin",
        "vc_mandible_claw",
        "oc_tentacle_arm",
        "bw_foreclaw",
        "vd_nematocyst",
        "mh_spore_pod",
        "hs_wing_membrane",
        "ms_leg_tarsus",
        "hc_shell_whorl",
        "ma_cuticle_molt",
        "gm_folded_wing",
        "fs_arm_segment",
        "sd_wing_membrane",
        "ce_swimmeret_lobe",
        "st_plastron_shard",
        "vm_wing_sheet",
    ],
    "geothermal": [
        "gw_cardiac_node",
        "vc_antenna_cluster",
        "oc_chitin_beak",
        "bw_ribcage",
        "vd_neural_mesh",
        "mh_mycelium_root",
        "hs_thorax_plate",
        "ms_pedipalp",
        "hc_septum_plate",
        "ma_ganglion_node",
        "gm_raptorial_claw",
        "fs_stalk_columnal",
        "sd_obsidian_scale",
        "ce_mouth_disc",
        "st_limb_claw",
        "vm_gill_filament",
    ],
    "volcanic": [
        "gw_jaw_fang",
        "vc_walking_leg",
        "oc_ink_sac",
        "bw_hindlimb",
        "vd_photophore",
        "mh_chitin_node",
        "hs_abdomen_segment",
        "ms_abdomen_sclerite",
        "hc_beak",
        "ma_chitinous_seta",
        "gm_abdominal_sheath",
        "fs_oral_tegmen",
        "sd_tail_barb",
        "ce_great_appendage",
        "st_beak",
        "vm_tail_barb",
    ],
    "deep": [
        "gw_spinal_vertebra",
        "vc_eye_stalk",
        "oc_lens_eye",
        "bw_tail_spike",
        "vd_tendril",
        "mh_stigmatic_disc",
        "hs_compound_eye",
        "ms_eye_cluster",
        "hc_tentacle_crown",
        "ma_luminous_ring",
        "gm_antennal_whip",
        "fs_holdfast_rootlet",
        "sd_talon",
        "ce_cephalic_photophore",
        "st_carapace_neural",
        "vm_ventral_photophore",
    ],
}


def open_orders(orders, biome):
    found = []
    for order in orders:
        if order.status != "complete" and order.biome == biome:
            found.append(order)
    return found


def stock_of(orders, inventory):
    """Units of each required fragment already sitting in Inventory (home base only)."""
    stock = {}
    for order in orders:
        for fragment_id in order.requires:
            if inventory is None:
                stock[fragment_id] = 0
            else:
                stock[fragment_id] = inventory.count(fragment_id)
    return stock


def units_needed(orders, in_stock, pending):
    # Largest shortfall across the open orders: a fragment needed by two orders is one unit of
    # work, not two, so the sum would overcount.
    needed = {}
    for order in orders:
        for fragment_id, wanted in order.requires.items():
            short = wanted - order.delivered.get(fragment_id, 0)
            short -= order.in_transit.get(fragment_id, 0)
            short -= in_stock.get(fragment_id, 0)
            short -= pending.get(fragment_id, 0)
            if short > needed.get(fragment_id, 0):
                needed[fragment_id] = short
    return needed


def specimen_fragment(specimen, locations):
    """Fragment id of a specimen, or None while it is unidentified.

    A collected specimen reports no fragment until analysis, so its coords are matched against
    the scan: a cataloged location at the same coords is the same fragment.
    """
    if specimen is None:
        return None
    if specimen.fragment_id is not None:
        return specimen.fragment_id
    for location in locations:
        if location.cataloged and location.coords == specimen.coords:
            return location.fragment_id
    return None


def pending_counts(specimens, locations):
    counts = {}
    for specimen in specimens:
        fragment_id = specimen_fragment(specimen, locations)
        if fragment_id is not None:
            counts[fragment_id] = counts.get(fragment_id, 0) + 1
    return counts


def lab_specimen(lab):
    """The specimen in the Bio Lab chamber, or None when it cannot be read."""
    if lab is None:
        return None
    try:
        return lab.specimen
    except Exception:
        # Boundary: an unreadable chamber must not stop collection. Only the cargo slot counts.
        return None


def cataloged_ids(journal):
    """Fragment ids already in the Journal for this planet. None when the Journal is absent."""
    if journal is None:
        return None
    return [entry.fragment_id for entry in journal.cataloged_fragments(PLANET_ID)]


def exploring_can_help(biome, known):
    """True while the biome has a fragment type the Journal does not hold yet.

    An unknown biome, or no Journal, keeps exploring on: there is nothing to compare against.
    """
    if known is None or biome not in BIOME_FRAGMENTS:
        return True
    missing = [fragment_id for fragment_id in BIOME_FRAGMENTS[biome] if fragment_id not in known]
    return len(missing) > 0


def pick_target(locations, needed, explore):
    for location in locations:
        if location.cataloged and needed.get(location.fragment_id, 0) > 0:
            return location
    if not explore:
        return None
    for location in locations:
        if not location.cataloged:
            return location
    return None


def blocked(message):
    print("warning: " + message)
    set_status(message, "warn")
    sleep(PAUSE_SECONDS)


while True:
    if self.cargo is not None:
        set_status("holding a specimen for the Bio Lab", "info")
        sleep(RETRY_SECONDS)
        continue

    locations = self.scan()
    exchange = get_component(EXCHANGE_ID)
    inventory = get_component("inventory")
    lab = get_component(LAB_ID)

    orders = []
    if exchange is not None:
        orders = open_orders(exchange.orders(), self.outpost.biome)
    needed = units_needed(
        orders,
        stock_of(orders, inventory),
        pending_counts([lab_specimen(lab)], locations),
    )

    journal = get_component(JOURNAL_ID)
    explore = exploring_can_help(self.outpost.biome, cataloged_ids(journal))
    target = pick_target(locations, needed, explore)
    if target is None:
        set_status("no fragment to collect for the open Bio Orders", "info")
        sleep(PAUSE_SECONDS)
        continue

    result = self.collect(target.coords)
    if result.status == "ok":
        set_status("collected a specimen " + str(target.distance) + " m away", "info")
    elif result.status == "busy":
        sleep(RETRY_SECONDS)
    else:
        blocked("collect " + result.status + ": " + result.message)
