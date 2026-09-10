// Mount-prefix base for every Statistics client call. SINGLE DECLARATION.
//
// scitex-app's `stx-mount` contract (scitex-app >= 0.8.0): the SERVER declares
// where the app is mounted; the browser joins endpoint names onto it.
//
// THE PREFIX NEVER ENDS IN "/". Root is "" standalone, "/apps/u/stats" when
// the hub embeds us. So ENDPOINT NAMES CARRY THE LEADING SLASH:
// STX_MOUNT + "/api/run". A missing marker is a broken contract and we THROW
// rather than silently defaulting to root (a wrong default exfiltrates to a
// protocol-relative URL; a missing marker should fail where it breaks).
const _stxMountEl = document.querySelector('meta[name="stx-mount"]');
if (!_stxMountEl) {
  throw new Error(
    'stx-mount marker missing: the page was not served by a scitex-app ' +
    'shell, or the template stopped emitting it. The Statistics UI cannot ' +
    'build API URLs without knowing its mount prefix.'
  );
}
const STX_MOUNT = _stxMountEl.content;
