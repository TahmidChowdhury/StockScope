export type ReferenceLabel = 'negative' | 'neutral' | 'positive'
export type Prediction = {
  status: string
  label: string | null
  score?: number
  token_truncated?: boolean
  input_tokens?: number
  max_tokens?: number
  probabilities?: Record<string, number> | null
}
export type ToneModel = {
  key: string
  model_id: string
  revision: string
  source_url: string
  license: string
  provenance: string
  caveat: string
  status: string
  message: string
  load_latency_ms?: number
  inference_latency_ms?: number
}
export type ToneReport = {
  symbol: string
  generated_at: string
  elapsed_ms: number
  text_scope: string
  language_policy: string
  sample: {
    requested: number
    returned: number
    eligible: number
    empty_text: number
    unknown_language: number
    unsupported_language: number
    company_release_excluded: number
  }
  baseline: { model_id: string; revision: string | null; license: string }
  challengers: ToneModel[]
  evaluation: {
    status: string
    annotation_count: number
    label_source: string
    metric_policy: string
    models: Record<
      string,
      {
        status: string
        evaluated_count: number
        macro_f1?: number
        accuracy?: number
        all_three_classes_present?: boolean
      }
    >
  }
  rows: {
    sample_id: string
    text_sha256: string
    title: string
    text: string
    url: string | null
    source: string | { name?: string | null } | null
    published_at: string | null
    status: string
    coverage: string
    character_truncated: boolean
    predictions: Record<string, Prediction>
  }[]
}
export interface ScenarioDraft {
  version: 1
  cashFlow: string
  shares: string
  currency: string | null
  scenarios: { name: string; change: string; multiple: string }[]
}
export interface ToneAnnotation {
  sample_id: string
  text_sha256: string
  label: ReferenceLabel
}
export interface ToneDraft {
  version: 1
  report: ToneReport | null
  annotations: Record<string, ToneAnnotation>
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
const string = (value: unknown, max = 12000): value is string =>
  typeof value === 'string' && value.length <= max
const optionalString = (value: unknown, max = 12000) =>
  value === null || string(value, max)
const finite = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value)
const count = (value: unknown) =>
  finite(value) && Number.isInteger(value) && value >= 0 && value <= 30
const label = (value: unknown): value is ReferenceLabel =>
  value === 'negative' || value === 'neutral' || value === 'positive'
const identity = (value: unknown, length: number) =>
  typeof value === 'string' &&
  value.length === length &&
  /^[a-f0-9]+$/.test(value)
const input = (value: unknown): value is string =>
  string(value, 64) &&
  (value === '' || /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d*)?$/i.test(value))

export function isScenarioDraft(value: unknown): value is ScenarioDraft {
  if (
    !record(value) ||
    value.version !== 1 ||
    !input(value.cashFlow) ||
    !input(value.shares) ||
    !(
      value.currency === null ||
      (typeof value.currency === 'string' && /^[A-Z]{3}$/.test(value.currency))
    ) ||
    !Array.isArray(value.scenarios) ||
    value.scenarios.length !== 3
  )
    return false
  return value.scenarios.every(
    (row, index) =>
      record(row) &&
      row.name === ['Bear', 'Base', 'Bull'][index] &&
      input(row.change) &&
      input(row.multiple),
  )
}

function isPrediction(value: unknown): value is Prediction {
  if (
    !record(value) ||
    !string(value.status, 80) ||
    !(value.label === null || label(value.label))
  )
    return false
  if (
    value.score !== undefined &&
    (!finite(value.score) || value.score < -1 || value.score > 1)
  )
    return false
  for (const key of ['input_tokens', 'max_tokens'])
    if (value[key] !== undefined && (!finite(value[key]) || value[key] < 0))
      return false
  if (
    value.token_truncated !== undefined &&
    typeof value.token_truncated !== 'boolean'
  )
    return false
  if (value.probabilities !== undefined && value.probabilities !== null) {
    if (!record(value.probabilities)) return false
    const probabilities = value.probabilities
    if (
      !['negative', 'neutral', 'positive'].every(
        (key) =>
          finite(probabilities[key]) &&
          probabilities[key] >= 0 &&
          probabilities[key] <= 1,
      )
    )
      return false
  }
  return true
}

export function isToneReport(value: unknown): value is ToneReport {
  if (
    !record(value) ||
    !string(value.symbol, 12) ||
    !/^[A-Z][A-Z0-9.-]{0,11}$/.test(value.symbol) ||
    !string(value.generated_at, 80) ||
    !Number.isFinite(Date.parse(value.generated_at)) ||
    !finite(value.elapsed_ms) ||
    value.elapsed_ms < 0 ||
    !string(value.text_scope) ||
    !string(value.language_policy) ||
    !record(value.sample) ||
    !record(value.baseline) ||
    !record(value.evaluation) ||
    !Array.isArray(value.challengers) ||
    value.challengers.length !== 2 ||
    !Array.isArray(value.rows) ||
    value.rows.length > 30
  )
    return false
  const sample = value.sample
  if (
    ![
      'requested',
      'returned',
      'eligible',
      'empty_text',
      'unknown_language',
      'unsupported_language',
      'company_release_excluded',
    ].every((key) => count(sample[key]))
  )
    return false
  if (
    sample.returned !== value.rows.length ||
    !string(value.baseline.model_id, 200) ||
    !optionalString(value.baseline.revision, 100) ||
    !string(value.baseline.license, 200)
  )
    return false
  const evaluation = value.evaluation
  if (
    !string(evaluation.status, 80) ||
    !count(evaluation.annotation_count) ||
    !string(evaluation.label_source) ||
    !string(evaluation.metric_policy) ||
    !record(evaluation.models)
  )
    return false
  const metrics = evaluation.models
  if (
    !['vader', 'finsense', 'modernfinbert'].every((key) => {
      const metric = metrics[key]
      return (
        record(metric) &&
        string(metric.status, 80) &&
        count(metric.evaluated_count) &&
        (metric.macro_f1 === undefined ||
          (finite(metric.macro_f1) &&
            metric.macro_f1 >= 0 &&
            metric.macro_f1 <= 1)) &&
        (metric.accuracy === undefined ||
          (finite(metric.accuracy) &&
            metric.accuracy >= 0 &&
            metric.accuracy <= 1)) &&
        (metric.all_three_classes_present === undefined ||
          typeof metric.all_three_classes_present === 'boolean')
      )
    })
  )
    return false
  if (
    !value.challengers.every((model, index) => {
      if (!record(model) || model.key !== ['finsense', 'modernfinbert'][index])
        return false
      if (
        ![
          'model_id',
          'revision',
          'source_url',
          'license',
          'provenance',
          'caveat',
          'status',
          'message',
        ].every((key) => string(model[key]))
      )
        return false
      if (
        typeof model.source_url !== 'string' ||
        !model.source_url.startsWith('https://huggingface.co/')
      )
        return false
      return ['load_latency_ms', 'inference_latency_ms'].every(
        (key) =>
          model[key] === undefined || (finite(model[key]) && model[key] >= 0),
      )
    })
  )
    return false
  if (
    new Set(value.rows.map((row) => (record(row) ? row.sample_id : null)))
      .size !== value.rows.length
  )
    return false
  return value.rows.every((row) => {
    if (!record(row) || !record(row.predictions)) return false
    const predictions = row.predictions
    return (
      identity(row.sample_id, 24) &&
      identity(row.text_sha256, 64) &&
      string(row.title) &&
      string(row.text, 6000) &&
      optionalString(row.url, 4000) &&
      optionalString(row.published_at, 100) &&
      (row.source === null ||
        string(row.source, 1000) ||
        (record(row.source) &&
          (row.source.name === undefined ||
            row.source.name === null ||
            string(row.source.name, 1000)))) &&
      string(row.status, 80) &&
      string(row.coverage, 80) &&
      typeof row.character_truncated === 'boolean' &&
      ['vader', 'finsense', 'modernfinbert'].every((key) =>
        isPrediction(predictions[key]),
      )
    )
  })
}

export function isToneDraft(value: unknown): value is ToneDraft {
  if (
    !record(value) ||
    value.version !== 1 ||
    !(value.report === null || isToneReport(value.report)) ||
    !record(value.annotations) ||
    Object.keys(value.annotations).length > 500
  )
    return false
  return Object.entries(value.annotations).every(
    ([key, annotation]) =>
      record(annotation) &&
      identity(annotation.sample_id, 24) &&
      identity(annotation.text_sha256, 64) &&
      label(annotation.label) &&
      key === `${annotation.sample_id}:${annotation.text_sha256}`,
  )
}

export function sameToneSample(
  saved: ToneReport,
  current: ToneReport,
): boolean {
  if (
    saved.symbol !== current.symbol ||
    saved.rows.length !== current.rows.length
  )
    return false
  const identities = new Map(current.rows.map((row) => [row.sample_id, row]))
  return saved.rows.every((row) => {
    const other = identities.get(row.sample_id)
    return (
      other?.text_sha256 === row.text_sha256 &&
      other.status === row.status &&
      other.text === row.text
    )
  })
}

export function matchingToneAnnotations(
  annotations: Record<string, ToneAnnotation>,
  current: ToneReport | null,
): Record<string, ReferenceLabel> {
  const result: Record<string, ReferenceLabel> = {}
  for (const row of current?.rows || []) {
    const annotation = annotations[`${row.sample_id}:${row.text_sha256}`]
    if (
      row.status === 'eligible' &&
      annotation?.sample_id === row.sample_id &&
      annotation.text_sha256 === row.text_sha256
    )
      result[row.sample_id] = annotation.label
  }
  return result
}
