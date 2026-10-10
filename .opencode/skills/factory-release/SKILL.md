---
name: factory-release
description: Connect release preparation to the existing AppPublishing protocol and Fastlane without publication
---

Source of truth: `D:/AppPublishing/README.md`; read it only in an authorized release
session. Preserve its apps/publisher layout and existing StorePublishMatic settings.
Do not invent another publishing catalogue, credential system or protocol.

`python tool/factory.py release-preflight <app-root> --app-id <slug> --platform android --locale tr-TR` is local readiness only. Add selected platforms/locales explicitly; use canonical public metadata paths, never credential contents.
Fastlane has no universal safe dry-run. Never invoke an existing production lane
as a dry-run; the factory smoke Fastfile only prints a success marker.

Verify package/bundle/version, signing identity, source/artifact hashes, metadata,
privacy/declarations, real platform screenshots, current official store policies.
Signing/credential writes, billing/products and production upload need explicit
authorization. macOS/Xcode is required for iOS builds. Do not inspect private key
values, echo env secrets, copy existing app keys or confuse Android with iOS proof.
After authorized publishing: store readback, install production build, smoke/crash
and backend checks; monitoring only when requested. Existing protocol overrides
duplicate publishing conventions. Offline StorePublishMatic inspector avoids AI API.
