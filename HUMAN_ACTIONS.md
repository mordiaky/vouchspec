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

Stripe remains regression-only and is not a customer purchase path.
