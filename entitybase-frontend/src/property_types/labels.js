// Display names for property types.
//
// The API is the source of truth (GET /v1/property-datatypes); these are only
// the fallbacks used where the descriptor has not been loaded, so a page still
// renders a type it has not fetched yet.
const LABELS = {
  'wikibase-item': 'Item',
  string: 'String',
}

/** Human-readable name for a datatype id, or '' when unknown. */
export function propertyTypeLabel(datatypeId) {
  if (!datatypeId) return ''
  return LABELS[datatypeId] || datatypeId
}