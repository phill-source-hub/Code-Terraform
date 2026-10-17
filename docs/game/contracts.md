# Contracts and Transmitter

Source: in-game DOCS manual, build `fe9a45c`. Sections: "Contracts" (guide and reference), "Transmitter", types `Contract`, `ContractScript`, and the 15 contract subtypes (not extracted yet; see below). Tag: **VERIFIED (docs)**.

## What a contract is

- Earth-side programming puzzle. Script reads contract data, computes an answer, sends it back. Reward is for correctness.
- Contract state is contained. A wrong answer is safe to inspect and retry.
- Each contract has a briefing (Info tab), input data via `self.contract`, and a credit reward.

## Workflow

1. Open the contract from the Contracts page (View Contract).
2. Read the briefing.
3. Print `self.contract` to see its input fields.
4. Work out the answer in small steps; print intermediates.
5. Transmit (see below). Correct answer pays out immediately.

Example from the manual:

```python
c = self.contract
print(c)

transmitter = get_component("transmitter")
transmitter.connect("earth")
transmitter.transmit(c.id, answer)
```

## `Contract` (base, `self.contract`)

| Property | Type | Notes |
|----------|------|-------|
| `.id` | str | Used for transmitting answers. Values: `relay_hack`, `xenogenetics`, `corrupted_archive`, `sealed_vault`, `data_tablet`, `terminal_breach`, `drifting_signal`, `cold_boot`, `three_echoes`, `buried_five`, `the_loom`, `crosstalk`, `beat_the_system`, `core_sample`, `lattice`. |
| `.name` | str | Display name. |
| `.reward` | int | Credits on completion. |
| `.status` | str | `available` or `completed`. |

Each subtype (for example `LatticeContract`, `RelayHackContract`) adds its own API. **Not extracted yet.** Before writing a contract script, pull that subtype's entry from the manual into `docs/game/contracts-<name>.md`.

`ContractScript` (`self`, in contract scripts): `.name`, `.contract`.

Example of a subtype-specific result from the manual (for orientation only): `LatticeGrid.probe()` returns `LatticeProbeResult` with `.status` (`ok`, `node_tripped`, `lattice_tripped`), `.message`, `.reading` (int 0-8 when ok, else None). `Vault.escape()` returns `VaultEscapeResult` with `.status` (`ok`, `not_at_exit`), `.message`, `.key` (str when ok).

## Transmitter

- Sends named values to another planet. Used for contract answers and sensor readings to Earth.
- Access: `get_component("transmitter")`.
- A connection lasts only for the current script run. Every transmitting script must `connect()` first, again after a restart.

| Method | Returns | Notes |
|--------|---------|-------|
| `list_planets()` | list[Planet] | Call once at start. Pass `.id` to `connect`. |
| `connect(planet)` | ActionResult | Planet id, lowercase (for example `"earth"`). Read `get_info().target` after success. Statuses: `ok`, `not_found`. |
| `disconnect()` | ActionResult | Clears this object's channel only. Status: `ok`. |
| `get_info()` | TransmitterInfo | `.connected` bool, `.target` planet id or `"none"`. Guard before `transmit`. |
| `transmit(key, value)` | ActionResult | Contract answer: key is the contract id. Sensor readings: key is what Earth requests, for example `"current_temperature"`. |

`transmit` statuses:

| Status | Kind | Meaning |
|--------|------|---------|
| `correct` | success | Solved the active contract. Paid; contract completed. |
| `incorrect` | rejection | Wrong value. |
| `already_completed_correct` | success | Contract already done; this value is correct. |
| `already_completed_incorrect` | rejection | Contract already done; this value is wrong. |
| `accepted` | success | Telemetry reading matched the planet value. Uplink step, not a contract answer. |
| `rejected` | rejection | Value or request rejected. |
| `not_connected` | rejection | No active connection. |
| `wrong_planet` | rejection | Targets another planet. |
| `wrong_contract` | rejection | Contract not active for this operation. |
| `locked` | rejection | Feature or operation locked. |
| `unknown_contract` | rejection | Contract id does not exist. |
| `key_is_planet` | rejection | Key names a planet, not a telemetry or contract key. |
| `unknown_key` | rejection | Key does not exist. |

Sensor telemetry is unavailable until the power and sensor onboarding steps are complete and the uplink step is active.

## Commander and Shop (from the contracts guide)

```python
me = get_component("me")
print(me.get_credits())

shop = get_component("shop")
shop.sell("soil_sample")
shop.buy("solar_generator")
```

Shop `sell` returns `SaleResult` with `.status` (`ok`, `not_sellable`, `no_stock`), `.item_id`, `.units`, `.credits`.

## Open questions

- Per-contract APIs for all 15 subtypes: not extracted. Needed before any contract script.
- Whether a `transmit` on `correct` returns a payload with the reward: check in game.
- Shop `buy` status list: not extracted yet.
