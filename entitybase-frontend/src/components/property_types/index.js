// One component per property type, plus the registry that maps a type to it.
//
// The API serves the supported types (GET /v1/property-datatypes); the type
// decides which value input to render, so adding a property type means adding a
// component here and registering it. Nothing else needs to know.
import ItemValueInput from './ItemValueInput.vue'
import StringValueInput from './StringValueInput.vue'

// Datatype id -> value input component
const VALUE_INPUTS = {
  'wikibase-item': ItemValueInput,
  string: StringValueInput,
}

// Value kind -> fallback input, used when the API grows a type we have no
// dedicated component for yet: better a rough input than a broken form.
const VALUE_KIND_INPUTS = {
  entity: ItemValueInput,
  text: StringValueInput,
}

export const DEFAULT_VALUE_INPUT = StringValueInput

/** The value input component for a property type descriptor. */
export function valueInputFor(datatype) {
  if (!datatype) return null
  return (
    VALUE_INPUTS[datatype.id] || VALUE_KIND_INPUTS[datatype.value_kind] || null
  )
}

/** The value input for a bare datatype id, e.g. 'string'. */
export function valueInputForId(datatypeId) {
  if (!datatypeId) return null
  return VALUE_INPUTS[datatypeId] || null
}

export const PROPERTY_TYPE_COMPONENTS = VALUE_INPUTS