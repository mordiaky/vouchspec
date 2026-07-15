# Human actions

No owner action is currently requested. Do not request additional Coinbase SMS codes and do not
resume Coinbase portal automation.

The replacement CDP API key and rotated Wallet Secret already exist as encrypted secrets in the
main-branch-only `vouchspec-mainnet-remedies` GitHub environment. The Base-USDC-only 25-cent account
policy also exists. The first credential accidentally surfaced during portal validation was
revoked immediately before use and was never stored. The replacement remedy workflow remains
manually disabled and `VOUCHSPEC_REMEDIES_ENABLED=false`.

Continue only through documented CDP APIs or the official CDP CLI. If a future operation truly
requires an owner-only financial-account action, prepare it fully and ask once; do not trigger
repeated authentication messages.

The API-only provisioner is now merged and verified, but run `29385202893` failed on the first
read-only EVM account-list call. No policy lookup, account creation, funding, signing, or transaction
occurred. Do not retry with the current credential and do not ask the owner to repair it through the
portal. Mainnet remains disabled while autonomous work continues on non-Coinbase launch gates.

Stripe remains regression-only and is not a customer purchase path.
