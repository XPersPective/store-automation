# Release, presentation and maintenance

Inspect the existing release setup first: on this machine `D:/AppPublishing/README.md` and the selected
app's Fastlane files; elsewhere find the real current location and never require a fixed path. Do not
create a second catalog, credential schema or uploader.

## Evidence per platform

| Target | Candidate and local check | Separate remote evidence |
|---|---|---|
| Google Play | Final AAB, internal package/version, signature, relevant Android device flow, metadata/images/declarations | Account/app/track/version readback; review and rollout status |
| App Store | Archive/IPA, bundle/version/signing, required iOS device/simulator coverage, store material | App Store Connect build processing, the selected submission, approval and availability |
| Windows / macOS / Linux | Selected installer, MSIX, package or portable build; install, launch, update, uninstall | Selected channel/store/download and the published version |
| Web | Final bundle + deployment config; real browser and service flow | Target hosting URL, revision, environment and working access |
| CLI / internal | Package or install command on each selected OS | Published package version, or none when the channel is internal use |

A factory test is not app acceptance; an APK check does not prove the AAB, an Android screenshot does not
prove iOS, a debug simulator run does not prove a signed release. Start nothing for unselected platforms;
an unsupported adapter or environment is never success.

## One final candidate

Bind the source snapshot, artifact hash, embedded identity/version, signature check, device/locale
screenshots, metadata and remote version references to the same candidate. No release database: the
release task's Evidence lines (`[artifact]`, `[remote]`, `[visual]`) hold these references. A manifest
entry for an image does not mean the image was decoded or the UX accepted.

Positioning and the product name describe the real user need. Icon, screenshot order and story, short and
long description, localization, release notes, privacy and support links describe the same product. No
missing features, unfounded health/safety claims, fake ratings or keyword stuffing. ASO and web SEO follow
different rules; commercial success is not guaranteed.

Take visuals from the real final app; a marketing composition does not replace real device or interaction
evidence. View the final export; check text, localization and format; record the source and usage rights
of images, fonts and audio. Machine translation alone is not language quality. When the source changes,
recheck the affected images and texts.

Check current official sources for the target version: [Google preview assets](https://support.google.com/googleplay/android-developer/answer/9866151),
[Apple review](https://developer.apple.com/app-store/review/guidelines/),
[Fastlane supply](https://docs.fastlane.tools/actions/supply/), [deliver](https://docs.fastlane.tools/actions/deliver/).
Static limits do not stay valid forever.

## Authority and remote results

The user's existing full app/account/action/destination authority stands; do not ask again. If it is
missing, finish the reversible preparation, show the concrete candidate and ask only for the missing
external decision. A general "install the skill" or "build the app" request is not production store
authority. Never put credential contents into model context; existing native tools consume them by path
or reference. No automatic billing, signing or role changes. Never run a production lane "as a test".

States are reported separately: `LOCAL_PREPARED`, `UPLOADED`, `SUBMITTED`, `APPROVED`, `AVAILABLE`; each is
observed on the real target and no linear progression is assumed. Without account/app/channel/version/
status readback, a submission is not complete. An API "completed" status alone does not prove worldwide
availability.

Before any external operation write `- <operation> | not_started | readback: <command>` in the task's
`## External`; set `sent` right before the call and `confirmed` once the result is observed. A lost
response stays `response_unknown`, and boot stops every later agent with READBACK_FIRST. Compare the read
back result with `SA release-readback`, record `[remote]` evidence with `SA evidence`. Release tasks are
HIGH risk and need independent review.

## iOS and CI

A suitable macOS/Xcode machine or selected CI is required. Public standard runners, private quota, larger
runners and storage have separate cost terms; a plan name does not prove remaining free minutes. Do not
call anything free before the account, repository, runner and current cost limit are verified. Never
publish private source or user data for free CI. Never change budgets or billing.
[GitHub billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

## After release

Open small maintenance tasks from real support issues, suitable crash/performance data and applicable
SDK/store changes. No new tracking by default. If the user asked to monitor selected projects, use the
host's existing scheduler: silent when nothing changes, notify on meaningful change; no new daemon. A fix
renews the affected test/device/material/release evidence; it does not reopen every product decision.
