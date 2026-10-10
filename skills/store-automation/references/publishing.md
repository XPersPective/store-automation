# Publishing and private credentials

Read the existing `D:/AppPublishing/README.md` before release preparation. It owns the app/publisher layout and app records. Reuse existing Fastlane lanes and native Appfile/Deliverfile inputs; do not create another publication catalogue or custom uploader. Source projects remain independent repositories.

Canonical paths under `apps/<app-id>`:

| Target | Metadata | Screenshots |
|---|---|---|
| Google Play | `stores/google-play/metadata/<locale>` | `metadata/<locale>/images/phoneScreenshots`, relative to the Google Play store directory |
| App Store | `stores/app-store/metadata/<locale>` | `stores/app-store/screenshots/<locale>` |

Android Turkish is `tr-TR`; iOS Turkish is `tr`. Other locale support must be checked against the selected store. Shared support/legal facts can inform both stores, but each has its own native files and limits. Never invent translations, product claims or privacy declarations. Android screenshot uploads replace the existing set; verify completeness before upload. Do not reuse Android screenshots as evidence of an iOS build.

`tool/release.py:preflight` checks explicitly selected public source/version facts, canonical metadata, text lengths, HTTPS URL syntax, image headers/dimensions and release artifact hashes. It never opens credentials or contacts a store. Its passing result is **PREPARATION_ONLY**: image header inspection is neither image decoding, visual approval, device provenance nor compliance with changing store image specifications. Artifact hashes do not verify signing or embedded identity. Confirm those separately using official platform tools. Dynamic source identities are reported as unresolved. Missing or invalid local inputs return **BLOCKED**.

## Credential consumption

The user stores private material in the existing publishing credential locations, native CLI session store, OS keychain or CI secret manager. Agents receive references and access status only. Fastlane consumes Google credentials by native `json_key` path/WIF configuration, Apple credentials through `app_store_connect_api_key(key_filepath: ...)`, and signing through the project's established build integration. Do not read credential contents into model context, echo environment values, interpolate secrets into shell commands, copy another app's signing key, or attach raw credential-bearing logs. A tool process may read the private file directly without routing it through AI.

Skill rules and same-user subprocesses do **not** prevent an unrestricted agent from reading files under that OS user. Genuine enforcement requires an isolated broker/service identity with ACL-protected secrets, allowlisted operation arguments and private raw logs. A broker exposes sanitized status/results; it never accepts arbitrary shell text or returns secret content. Do not claim such isolation exists until it has been installed and independently tested. Native credential-by-path use reduces exposure but is not that security boundary.

Reuse valid official CLI authentication; login is requested only when unavailable/expired or when the user selects another account. Never handle passwords/2FA/recovery codes in the conversation. Subscription login does not imply metered API authorization. For account switching use the official CLI workflow; do not rotate accounts to evade quota.

Authorization belongs to the selected project and specifies target app, account, operation and release destination. Honor existing authorization without repeatedly asking. This skill's installation authorization does not authorize modifying an unrelated app, granting broad roles, enabling billing, deleting data or publishing a new product to production. Firestore/Cloudflare operations must use existing project configuration and credentials scoped to the required resources. Missing provider/app mapping is a blocker, not a reason to guess.

Before a store write verify signature, embedded identifier/version, remote latest version, complete actual-device screenshots, legal/declarations, account permissions and chosen test/review/production target. iOS build/signing requires macOS/Xcode or an appropriate macOS CI. Fastlane has no universal harmless dry-run: never run a production lane to test configuration. After an authorized upload, read back the actual track/version/status; submission is not store approval or global availability.

Official references (recheck current requirements before publishing): [supply](https://docs.fastlane.tools/actions/supply/), [deliver](https://docs.fastlane.tools/actions/deliver/), [App Store Connect API](https://docs.fastlane.tools/app-store-connect-api/).
