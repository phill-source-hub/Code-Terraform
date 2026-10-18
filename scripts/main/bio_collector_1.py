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
    bio_exchange.active_order(), inventory.count(item_id), journal.cataloged_fragments(planet_id),
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


def coords_key(coords):
    # A string, not a tuple: tuple() is not in the game's builtins list.
    return str(round(coords[0], 3)) + "," + str(round(coords[1], 3))


def known_dots(entries):
    """Map each identified dot's coords to its fragment id, from the Journal.

    A scan dot is marked cataloged only once that dot itself is analysed. A dot whose fragment
    type is already in the Journal can still show cataloged False, so the Journal's coords are
    the only way to tell it apart from an unknown dot.
    """
    dots = {}
    if entries is None:
        return dots
    for entry in entries:
        dots[coords_key(entry.coords)] = entry.fragment_id
    return dots


def identity(location, dots):
    """Fragment id of a scan dot, from the scan or else from the Journal. None when unknown."""
    if location.cataloged:
        return location.fragment_id
    return dots.get(coords_key(location.coords))


def specimen_fragment(specimen, locations, dots):
    """Fragment id of a specimen, or None while it is unidentified.

    A collected specimen reports no fragment until analysis, so its coords are matched against
    the scan: a dot with a known identity at the same coords is the same fragment.
    """
    if specimen is None:
        return None
    if specimen.fragment_id is not None:
        return specimen.fragment_id
    for location in locations:
        if location.coords == specimen.coords:
            return identity(location, dots)
    return None


def pending_counts(specimens, locations, dots):
    counts = {}
    for specimen in specimens:
        fragment_id = specimen_fragment(specimen, locations, dots)
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


def journal_entries(journal):
    """Journal entries for this planet, or None when the Journal is absent."""
    if journal is None:
        return None
    return journal.cataloged_fragments(PLANET_ID)


def exploring_can_help(biome, known):
    """True while the biome has a fragment type the Journal does not hold yet.

    An unknown biome, or no Journal, keeps exploring on: there is nothing to compare against.
    """
    if known is None or biome not in BIOME_FRAGMENTS:
        return True
    missing = [fragment_id for fragment_id in BIOME_FRAGMENTS[biome] if fragment_id not in known]
    return len(missing) > 0


def pick_target(locations, needed, explore, dots):
    for location in locations:
        fragment_id = identity(location, dots)
        if fragment_id is not None and needed.get(fragment_id, 0) > 0:
            return location
    if not explore:
        return None
    for location in locations:
        if identity(location, dots) is None:
            return location
    return None


def short_text(needed):
    """Compact "fragment:count" list for the status line, clipped so the line stays valid."""
    parts = [fragment_id + ":" + str(count) for fragment_id, count in needed.items()]
    return ", ".join(parts) if parts else "none"


def say(message, level):
    # The game rejects status text over 240 characters and then stops the script.
    set_status(message[:240], level)


def blocked(message):
    print("warning: " + message)
    say(message, "warn")
    sleep(PAUSE_SECONDS)


def matched_dots(locations, dots):
    count = 0
    for location in locations:
        if identity(location, dots) is not None:
            count += 1
    return count


while True:
    locations = self.scan()
    exchange = get_component(EXCHANGE_ID)
    inventory = get_component("inventory")
    lab = get_component(LAB_ID)

    # Only the Bio Order the Exchange is working on. Other open orders are served when the
    # Exchange moves to them, so collecting for all of them sends the collector after fragments
    # no delivery is waiting for.
    orders = []
    if exchange is not None:
        active = exchange.active_order()
        if active is not None:
            orders = open_orders([active], self.outpost.biome)
    journal = get_component(JOURNAL_ID)
    entries = journal_entries(journal)
    dots = known_dots(entries)
    known_types = None
    if entries is not None:
        known_types = [entry.fragment_id for entry in entries]
    explore = exploring_can_help(self.outpost.biome, known_types)

    needed = units_needed(
        orders,
        stock_of(orders, inventory),
        pending_counts([lab_specimen(lab)], locations, dots),
    )

    # Shown on the status line on every pass, so the inputs to a pick can be read off the game:
    # biome, open orders, Journal entries, dots identified, dots matched in the scan, units short
    # and whether exploring is allowed. Kept first so the clip at 240 characters cuts the end.
    diag = (
        "biome "
        + str(self.outpost.biome)
        + ", orders "
        + str(len(orders))
        + ", journal "
        + str(-1 if entries is None else len(entries))
        + ", dots "
        + str(matched_dots(locations, dots))
        + "/"
        + str(len(locations))
        + ", short "
        + short_text(needed)
        + ", explore "
        + str(explore)
    )

    if self.cargo is not None:
        say("holding a specimen for the Bio Lab; " + diag, "info")
        sleep(RETRY_SECONDS)
        continue

    target = pick_target(locations, needed, explore, dots)
    if target is None:
        say("idle, nothing picked; " + diag, "info")
        sleep(PAUSE_SECONDS)
        continue
    if identity(target, dots) is None:
        reason = "explore"
    else:
        reason = "order: " + str(identity(target, dots))

    result = self.collect(target.coords)
    if result.status == "ok":
        say("collected " + reason + "; " + diag, "info")
    elif result.status == "busy":
        sleep(RETRY_SECONDS)
    else:
        blocked("collect " + result.status + ": " + result.message)
