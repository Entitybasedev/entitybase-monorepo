// Pure structural diff between two entity revisions.
// Term values are hash-referenced in revision payloads; the resolvers
// fetch the human-readable values from the /v1/resolve endpoints.

function termHashes(revision, kind) {
  const hashes = revision?.data?.revision?.hashes?.[kind]
  return hashes ?? {}
}

function statementHashes(revision) {
  return revision?.data?.revision?.hashes?.statements ?? []
}

async function resolveTermTexts(hashesByLang, resolveFn) {
  const allHashes = Object.values(hashesByLang).flat().filter(Boolean)
  const resolved = await resolveFn(allHashes)
  const texts = {}
  for (const [lang, hash] of Object.entries(hashesByLang)) {
    if (!hash) continue
    texts[lang] = resolved[String(hash)] ?? null
  }
  return texts
}

function diffTerms(oldTexts, newTexts) {
  const langs = [...new Set([...Object.keys(oldTexts), ...Object.keys(newTexts)])]
  const entries = []
  for (const lang of langs) {
    const oldVal = oldTexts[lang] ?? null
    const newVal = newTexts[lang] ?? null
    if (oldVal === newVal) continue
    let status = 'changed'
    if (oldVal === null) status = 'added'
    else if (newVal === null) status = 'removed'
    entries.push({ lang, status, old: oldVal, new: newVal })
  }
  return entries
}

async function diffAliasLang(lang, oldHashes, newHashes, resolveFn) {
  const [oldResolved, newResolved] = await Promise.all([
    resolveFn(oldHashes),
    resolveFn(newHashes),
  ])
  const oldSet = [...new Set(oldHashes.map((h) => oldResolved[String(h)]).filter(Boolean))]
  const newSet = [...new Set(newHashes.map((h) => newResolved[String(h)]).filter(Boolean))]
  const added = newSet.filter((a) => !oldSet.includes(a))
  const removed = oldSet.filter((a) => !newSet.includes(a))
  if (!added.length && !removed.length) return null
  return { lang, added, removed }
}

async function resolveStatementValue(statementHash, getStatement, getSnak) {
  const res = await getStatement(statementHash)
  const stmt = res.statement
  const mainsnak =
    typeof stmt?.mainsnak === 'object'
      ? stmt.mainsnak
      : await getSnak(stmt?.mainsnak)
  if (!mainsnak?.datavalue) return { property: mainsnak?.property ?? '?', value: '?' }
  const dv = mainsnak.datavalue
  const value = dv.type === 'wikibase-item' ? (dv.value?.id ?? '?') : String(dv.value ?? '?')
  return { property: mainsnak.property, value }
}

export async function computeEntityDiff(oldRevision, newRevision, resolvers) {
  const { resolveLabels, resolveDescriptions, resolveAliases, getStatement, getSnak } =
    resolvers

  // --- Labels ---
  const oldLabels = await resolveTermTexts(
    termHashes(oldRevision, 'labels'),
    resolveLabels
  )
  const newLabels = await resolveTermTexts(
    termHashes(newRevision, 'labels'),
    resolveLabels
  )

  // --- Descriptions ---
  const oldDescriptions = await resolveTermTexts(
    termHashes(oldRevision, 'descriptions'),
    resolveDescriptions
  )
  const newDescriptions = await resolveTermTexts(
    termHashes(newRevision, 'descriptions'),
    resolveDescriptions
  )

  // --- Aliases ---
  const oldAliases = termHashes(oldRevision, 'aliases')
  const newAliases = termHashes(newRevision, 'aliases')
  const aliasLangs = [...new Set([...Object.keys(oldAliases), ...Object.keys(newAliases)])]
  const aliases = (
    await Promise.all(
      aliasLangs.map((lang) =>
        diffAliasLang(lang, oldAliases[lang] ?? [], newAliases[lang] ?? [], resolveAliases)
      )
    )
  ).filter(Boolean)

  // --- Statements ---
  const oldHashes = new Set(statementHashes(oldRevision).map(String))
  const newHashes = new Set(statementHashes(newRevision).map(String))
  const addedHashes = [...newHashes].filter((h) => !oldHashes.has(h))
  const removedHashes = [...oldHashes].filter((h) => !newHashes.has(h))

  const [added, removed] = await Promise.all([
    Promise.all(addedHashes.map((h) => resolveStatementValue(h, getStatement, getSnak))),
    Promise.all(removedHashes.map((h) => resolveStatementValue(h, getStatement, getSnak))),
  ])

  const labels = diffTerms(oldLabels, newLabels)
  const descriptions = diffTerms(oldDescriptions, newDescriptions)
  const hasChanges =
    labels.length || descriptions.length || aliases.length || added.length || removed.length

  return {
    hasChanges: Boolean(hasChanges),
    labels,
    descriptions,
    aliases,
    statements: {
      added,
      removed,
    },
  }
}
