// Module-level cache that survives component unmounts (i.e. tab switches).
// React resets local state when a page unmounts, so revisiting a tab normally
// blanks the screen and shows a loading flash before data returns. Keeping the
// last successful payload here lets a page render its previous data instantly,
// then refresh in the background without a visible reload.

const store = new Map()

export function getCache(key) {
  return store.has(key) ? store.get(key) : null
}

export function setCache(key, value) {
  store.set(key, value)
}
