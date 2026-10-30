'use client'

import AnimatedSelect from '@/components/ui/AnimatedSelect'

import AnimatedAccordion from '@/components/ui/AnimatedAccordion'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Download, FlaskConical, Play, RefreshCw } from 'lucide-react'
import { apiFetch } from '@/lib/api'

import { useWorkspaceDraft } from '@/hooks/useWorkspaceDraft'
import { valuationDate } from '@/lib/valuation'
import {
  isToneDraft,
  isToneReport,
  matchingToneAnnotations,
  sameToneSample,
  type Prediction,
  type ToneReport as Report,
  type ReferenceLabel,
  type ToneDraft,
} from '@/lib/company-drafts'

const statusLabel = (value: string) => value.replaceAll('_', ' ')
const emptyDraft: ToneDraft = { version: 1, report: null, annotations: {} }

function articleLink(value: string | null) {
  try {
    const url = new URL(value || '')
    return url.protocol === 'https:' ? url.href : null
  } catch {
    return null
  }
}

function publication(value: string | null) {
  if (!value || !Number.isFinite(Date.parse(value)))
    return 'Publication date unavailable'
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'America/New_York',
  }).format(new Date(value))
}

function saveJson(value: unknown, filename: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }),
  )
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function Tone({ prediction }: { prediction: Prediction }) {
  if (prediction.status !== 'scored' || !prediction.label) {
    return (
      <span className="text-xs text-white/40">
        {statusLabel(prediction.status)}
      </span>
    )
  }
  const tone =
    prediction.label === 'positive'
      ? 'text-emerald-300'
      : prediction.label === 'negative'
        ? 'text-rose-300'
        : 'text-amber-200'
  return (
    <div className="space-y-1">
      <p className={`text-sm capitalize ${tone}`}>{prediction.label}</p>
      <p className="text-xs tabular-nums text-white/50">
        {prediction.score != null
          ? `${prediction.score >= 0 ? '+' : ''}${prediction.score.toFixed(3)}`
          : '—'}
      </p>
      {prediction.token_truncated && (
        <p className="text-xs text-amber-200/80">
          First {prediction.max_tokens} of {prediction.input_tokens} tokens
        </p>
      )}
      {prediction.probabilities && (
        <AnimatedAccordion className="pt-1 text-[11px] text-white/40" triggerClassName="" title="Distribution">
          <div className="mt-2 space-y-1">
            {['negative', 'neutral', 'positive'].map((label) => (
              <p key={label} className="capitalize">
                {label}:{' '}
                {((prediction.probabilities?.[label] ?? 0) * 100).toFixed(1)}%
              </p>
            ))}
            <p>Uncalibrated model softmax</p>
          </div>
        </AnimatedAccordion>
      )}
    </div>
  )
}

export default function SentimentLabPanel({ symbol }: { symbol: string }) {
  return <CompanyToneWorkspace key={symbol} symbol={symbol} />
}

function CompanyToneWorkspace({ symbol }: { symbol: string }) {
  const validateDraft = useCallback(
    (value: unknown): value is ToneDraft =>
      isToneDraft(value) &&
      (value.report === null || value.report.symbol === symbol),
    [symbol],
  )
  const {
    value: draft,
    setValue,
    ready,
    status,
    savedAt,
    message,
    generation,
    reset,
  } = useWorkspaceDraft<ToneDraft>(
    `company:${symbol}:tone-lab`,
    emptyDraft,
    validateDraft,
  )
  const draftRef = useRef(draft)
  draftRef.current = draft
  const [report, setReport] = useState<Report | null>(null)
  const [restoredSnapshot, setRestoredSnapshot] = useState(false)
  const [checkedAt, setCheckedAt] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [labelling, setLabelling] = useState(false)
  const annotations = matchingToneAnnotations(draft.annotations, report)
  const withheldCount =
    Object.keys(draft.annotations).length - Object.keys(annotations).length
  const mismatchedReport =
    !!draft.report && !!report && !sameToneSample(draft.report, report)
  const requestId = useRef(0)
  const invalidateRequests = useCallback(() => {
    requestId.current++
  }, [])

  const load = useCallback(
    async (compare = false, restoreSaved = false) => {
      if (!ready) return
      const current = ++requestId.current
      setBusy(true)
      setError(null)
      setLabelling(false)
      try {
        const response = await apiFetch(
          `/api/sentiment-lab/${encodeURIComponent(symbol)}?limit=12&compare=${compare}`,
        )
        const data = await response.json()
        if (!response.ok)
          throw new Error(
            typeof data.detail === 'string'
              ? data.detail
              : 'Could not read the sentiment research sample.',
          )
        if (!isToneReport(data) || data.symbol !== symbol)
          throw new Error(
            'The tone report has an unsupported format. Your saved workspace has been kept.',
          )
        if (current === requestId.current) {
          const saved = draftRef.current.report
          const restore =
            !compare &&
            restoreSaved &&
            saved !== null &&
            sameToneSample(saved, data)
          setReport(restore ? saved : data)
          setRestoredSnapshot(restore)
          setCheckedAt(data.generated_at)
          if (compare)
            setValue((previous) => ({ ...previous, report: data }), generation)
        }
      } catch (cause) {
        if (current === requestId.current)
          setError(
            cause instanceof Error
              ? cause.message
              : 'Could not read the sentiment research sample.',
          )
      } finally {
        if (current === requestId.current) setBusy(false)
      }
    },
    [symbol, ready, setValue, generation],
  )

  useEffect(() => {
    setReport(null)
    setRestoredSnapshot(false)
    setCheckedAt(null)
    if (ready) void load(false, true)
    return invalidateRequests
  }, [load, invalidateRequests, ready])

  const exportTemplate = async () => {
    setError(null)
    try {
      const response = await apiFetch(
        `/api/sentiment-lab/${encodeURIComponent(symbol)}/labels?limit=12`,
      )
      if (!response.ok)
        throw new Error('Could not export the annotation template.')
      saveJson(await response.json(), `${symbol}-tone-label-template.json`)
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : 'Could not export the annotation template.',
      )
    }
  }

  const evaluateLabels = async () => {
    if (!report) return
    const current = ++requestId.current
    const labels = report.rows
      .filter((row) => annotations[row.sample_id] && row.status === 'eligible')
      .map((row) => ({
        sample_id: row.sample_id,
        text_sha256: row.text_sha256,
        label: annotations[row.sample_id],
      }))
    if (!labels.length) return
    setBusy(true)
    setError(null)
    try {
      const response = await apiFetch(
        `/api/sentiment-lab/${encodeURIComponent(symbol)}/evaluate`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ limit: 12, labels }),
        },
      )
      const data = await response.json()
      if (!response.ok)
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : 'Could not evaluate the supplied labels.',
        )
      if (!isToneReport(data) || data.symbol !== symbol)
        throw new Error(
          'The evaluated tone report has an unsupported format. Your labels have been kept.',
        )
      if (current === requestId.current) {
        setReport(data)
        setRestoredSnapshot(false)
        setCheckedAt(data.generated_at)
        setValue((previous) => ({ ...previous, report: data }), generation)
      }
    } catch (cause) {
      if (current === requestId.current)
        setError(
          cause instanceof Error
            ? cause.message
            : 'Could not evaluate the supplied labels.',
        )
    } finally {
      if (current === requestId.current) setBusy(false)
    }
  }

  return (
    <section className="space-y-6 rounded-2xl border border-white/10 bg-[#16161e] p-4 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-violet-300">
            <FlaskConical className="h-4 w-4" /> Research preview
          </div>
          <h2 className="text-xl font-semibold text-white">Article tone lab</h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-white/55">
            Compare VADER with local finance models on saved {symbol} headlines
            and descriptions. Tone helps read the news; it does not establish
            whether a stock is worth buying.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={busy || !ready}
          className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm text-white/70 hover:bg-white/5 disabled:opacity-40"
        >
          <RefreshCw className={`h-4 w-4 ${busy ? 'animate-spin' : ''}`} />{' '}
          Reload sample
        </button>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-white/45">
        <p role="status">
          {!ready
            ? 'Reading your saved tone workspace…'
            : status === 'saved'
              ? `Saved in this browser · ${valuationDate(savedAt)}`
              : 'Completed comparisons and your labels are kept in this browser when storage is available.'}
          {message ? ` ${message}` : ''}
        </p>
        <button
          type="button"
          disabled={busy || !ready}
          onClick={() => {
            invalidateRequests()
            reset()
            setReport(null)
            setLabelling(false)
          }}
          className="rounded-lg border border-white/10 px-3 py-2 text-xs text-white/60 hover:bg-white/5 disabled:opacity-40"
        >
          Clear local tone workspace
        </button>
      </div>
      {restoredSnapshot && report && (
        <p
          role="status"
          className="rounded-lg border border-amber-300/15 bg-amber-300/5 p-3 text-xs leading-6 text-amber-100/80"
        >
          Saved comparison from {valuationDate(report.generated_at)} · stale
          model snapshot, not rerun. Current article IDs, text hashes and
          eligibility were checked at {valuationDate(checkedAt)}. Compare
          article tone to generate new results; Reload sample shows the current
          server baseline.
        </p>
      )}
      {mismatchedReport && draft.report && (
        <p
          role="status"
          className="rounded-lg border border-amber-300/15 bg-amber-300/5 p-3 text-xs leading-6 text-amber-100/80"
        >
          The saved comparison from {valuationDate(draft.report.generated_at)}{' '}
          belongs to a different article sample and is withheld. The current
          server baseline is shown. Your older report and labels remain in this
          browser until you replace the comparison or clear this workspace.
        </p>
      )}
      {report && withheldCount > 0 && (
        <p role="status" className="text-xs leading-6 text-amber-100/75">
          {withheldCount} saved annotation
          {withheldCount === 1 ? ' is' : 's are'} withheld because the article
          ID, text hash or current eligibility no longer matches this sample.
          These labels remain saved and are excluded from evaluation.
        </p>
      )}

      {error && (
        <p
          role="alert"
          className="rounded-lg border border-rose-400/20 bg-rose-400/5 p-3 text-sm text-rose-200"
        >
          {error}
        </p>
      )}
      {!report && !busy && ready && draft.report && (
        <p className="text-xs leading-6 text-amber-100/75">
          Your comparison from {valuationDate(draft.report.generated_at)}{' '}
          remains saved. Its article identities could not be verified against
          the current server sample, so the old results are withheld. Reload the
          sample to try again.
        </p>
      )}
      {!report && busy && (
        <p role="status" className="text-sm text-white/50">
          Reading saved news and local model availability…
        </p>
      )}

      {report && (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
              <p className="text-xs text-white/45">Saved sample</p>
              <p className="mt-1 text-lg font-medium text-white">
                {report.sample.returned}{' '}
                <span className="text-sm text-white/40">
                  of up to {report.sample.requested}
                </span>
              </p>
              <p className="mt-1 text-xs text-white/45">
                Latest saved news, not a representative test set
              </p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
              <p className="text-xs text-white/45">English text eligible</p>
              <p className="mt-1 text-lg font-medium text-white">
                {report.sample.eligible}{' '}
                <span className="text-sm text-white/40">
                  of {report.sample.returned}
                </span>
              </p>
              <p className="mt-1 text-xs text-white/45">
                {report.sample.unknown_language} unknown ·{' '}
                {report.sample.unsupported_language} other language ·{' '}
                {report.sample.empty_text} empty ·{' '}
                {report.sample.company_release_excluded} company releases
                excluded
              </p>
            </div>
            <div className="rounded-xl border border-violet-400/15 bg-violet-400/5 p-4">
              <p className="text-xs text-violet-200/60">
                Reference-label evaluation
              </p>
              <p className="mt-1 text-lg font-medium text-violet-100">
                {report.evaluation.status === 'evaluated'
                  ? `${report.evaluation.annotation_count} supplied labels`
                  : 'Not evaluated'}
              </p>
              <p className="mt-1 text-xs text-white/45">
                {report.evaluation.status === 'evaluated'
                  ? 'Self-labelled sample; not independent validation.'
                  : 'No human labels supplied. Model agreement is not accuracy.'}{' '}
                Investment usefulness remains unevaluated.
              </p>
            </div>
          </div>

          <p className="text-xs leading-relaxed text-white/45">
            {report.text_scope} VADER remains the production baseline (
            {report.baseline.revision || 'version unavailable'},{' '}
            {report.baseline.license}). Comparisons never rewrite saved scores.{' '}
            {report.language_policy}
          </p>

          <div className="grid gap-3 lg:grid-cols-2">
            {report.challengers.map((model) => (
              <article
                key={model.key}
                className="rounded-xl border border-white/10 p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-sm font-medium text-white">
                    {model.key === 'finsense'
                      ? 'FinSense ModernBERT'
                      : 'ModernFinBERT'}
                  </h3>
                  <span className="rounded-full border border-violet-400/20 bg-violet-400/5 px-2 py-1 text-xs capitalize text-violet-200">
                    {statusLabel(model.status)}
                  </span>
                </div>
                <p className="mt-3 text-xs leading-relaxed text-amber-200/65">
                  {model.caveat}
                </p>
                <p className="mt-3 text-xs text-white/45">{model.message}</p>
                {model.inference_latency_ms != null && (
                  <p className="mt-1 text-xs tabular-nums text-white/40">
                    Inference {model.inference_latency_ms.toFixed(0)} ms · load{' '}
                    {model.load_latency_ms?.toFixed(0) ?? '—'} ms
                  </p>
                )}
                <AnimatedAccordion className="mt-3 text-xs text-white/50" triggerClassName="text-violet-300" title="Model details and terms">
                  <div className="mt-3 space-y-2">
                    <a
                      href={model.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block break-all text-violet-300 hover:underline"
                    >
                      {model.model_id}
                    </a>
                    <p className="break-all font-mono text-[10px] text-white/35">
                      Revision {model.revision}
                    </p>
                    <p className="leading-relaxed">{model.provenance}</p>
                    <p>{model.license}</p>
                  </div>
                </AnimatedAccordion>
              </article>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void load(true)}
              disabled={busy || report.sample.eligible === 0}
              className="inline-flex items-center gap-2 rounded-lg bg-violet-500 px-4 py-2 text-sm font-medium text-white hover:bg-violet-400 disabled:opacity-40"
            >
              <Play className="h-4 w-4" />
              {busy ? 'Working locally…' : 'Compare article tone'}
            </button>
            <button
              type="button"
              onClick={() => void exportTemplate()}
              disabled={busy || !report.rows.length}
              className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm text-white/70 hover:bg-white/5 disabled:opacity-40"
            >
              <Download className="h-4 w-4" /> Export blank label template
            </button>
            <button
              type="button"
              onClick={() => saveJson(report, `${symbol}-tone-research.json`)}
              disabled={busy}
              className="rounded-lg border border-white/10 px-3 py-2 text-sm text-white/70 hover:bg-white/5 disabled:opacity-40"
            >
              Export preview
            </button>
            <button
              type="button"
              onClick={() =>
                saveJson(
                  { ...draft, symbol, saved_at: savedAt },
                  `${symbol}-tone-workspace.json`,
                )
              }
              disabled={busy || !ready}
              className="rounded-lg border border-white/10 px-3 py-2 text-sm text-white/70 hover:bg-white/5 disabled:opacity-40"
            >
              Export local workspace
            </button>
            <button
              type="button"
              onClick={() => setLabelling((value) => !value)}
              disabled={busy || report.sample.eligible === 0}
              className="rounded-lg border border-white/10 px-3 py-2 text-sm text-white/70 hover:bg-white/5 disabled:opacity-40"
            >
              {labelling ? 'Hide label controls' : 'Label this sample'}
            </button>
          </div>
          <p className="text-xs text-white/40">
            Only pinned local weights run. Missing models stay unavailable.
            Supply your own reference labels to measure agreement on this
            sample. Labels and completed reports are saved in this browser for
            this company and access role, and evaluation exports include
            submitted labels. Saved news is unchanged.
          </p>

          {labelling && (
            <div className="rounded-xl border border-violet-400/15 bg-violet-400/5 p-4">
              <h3 className="text-sm font-medium text-violet-100">
                Your reference labels
              </h3>
              <p className="mt-2 text-xs leading-relaxed text-white/55">
                Inspect each saved input below and label its tone toward{' '}
                {symbol}. Leave mixed, irrelevant or uncertain text unlabelled.
                Your annotations are not independently verified. Reloading the
                sample restores only labels whose article ID and text hash still
                match; other labels are kept but withheld.
              </p>
              <button
                type="button"
                onClick={() => void evaluateLabels()}
                disabled={busy || Object.keys(annotations).length === 0}
                className="mt-3 rounded-lg bg-violet-500 px-3 py-2 text-sm font-medium text-white hover:bg-violet-400 disabled:opacity-40"
              >
                Evaluate supplied labels ({Object.keys(annotations).length})
              </button>
            </div>
          )}

          {report.evaluation.status === 'evaluated' && (
            <div className="rounded-xl border border-white/10 p-4">
              <p className="text-xs text-white/50">
                {report.evaluation.label_source}
              </p>
              <p className="mt-2 text-xs text-white/40">
                Metrics reflect your last submitted labels. Evaluate again after
                editing them.
              </p>
              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                {['vader', 'finsense', 'modernfinbert'].map((key) => {
                  const metric = report.evaluation.models[key]
                  return (
                    <div key={key} className="rounded-lg bg-white/[0.025] p-3">
                      <p className="text-sm text-white/75">
                        {key === 'vader'
                          ? 'VADER'
                          : key === 'finsense'
                            ? 'FinSense'
                            : 'ModernFinBERT'}
                      </p>
                      {metric.status === 'evaluated' ? (
                        <>
                          <p className="mt-2 text-sm tabular-nums text-violet-200">
                            Macro-F1 {metric.macro_f1?.toFixed(3)} ·{' '}
                            {metric.evaluated_count} scored labels
                          </p>
                          <p className="mt-1 text-xs text-white/45">
                            Agreement{' '}
                            {((metric.accuracy ?? 0) * 100).toFixed(1)}%
                            {!metric.all_three_classes_present
                              ? ' · fewer than 3 reference classes'
                              : ''}
                          </p>
                        </>
                      ) : (
                        <p className="mt-2 text-xs text-white/40">
                          Not evaluated · no scored labelled rows
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>
              <p className="mt-3 text-xs leading-relaxed text-white/40">
                {report.evaluation.metric_policy} These results do not evaluate
                investment performance.
              </p>
            </div>
          )}

          {!report.rows.length ? (
            <p className="rounded-lg border border-dashed border-white/10 p-6 text-sm text-white/45">
              No saved news is available for {symbol}. Collect sources from
              Research summary, then reload this sample.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-white/10">
              <table className="w-full min-w-[680px] text-left">
                <caption className="sr-only">
                  Saved headline tone comparison; scores use different scales
                  and are not return forecasts
                </caption>
                <thead className="bg-white/[0.025] text-xs text-white/45">
                  <tr>
                    <th className="p-3 font-medium">Saved text</th>
                    <th className="p-3 font-medium">VADER</th>
                    <th className="p-3 font-medium">FinSense</th>
                    <th className="p-3 font-medium">ModernFinBERT</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {report.rows.map((row, index) => (
                    <tr key={row.sample_id}>
                      <td className="max-w-sm p-3 align-top">
                        <p className="text-sm leading-relaxed text-white/80">
                          {row.title || 'Untitled saved record'}
                        </p>
                        <p className="mt-1 text-xs text-white/35">
                          {row.coverage.replace('+', ' + ')} ·{' '}
                          {statusLabel(row.status)}
                          {row.character_truncated
                            ? ' · text capped at 6,000 characters'
                            : ''}
                        </p>
                        <p className="mt-2 text-xs text-white/40">
                          {typeof row.source === 'string'
                            ? row.source
                            : row.source?.name || 'Source unavailable'}{' '}
                          · {publication(row.published_at)}
                        </p>
                        <AnimatedAccordion className="mt-2 text-xs text-white/50" triggerClassName="text-violet-300" title="Inspect saved input">
                          <p className="mt-2 whitespace-pre-wrap break-words leading-relaxed">
                            {row.text || 'No text available'}
                          </p>
                          <p className="mt-2 text-white/35">
                            Input supplied to analysis; individual model token
                            limits are shown in its result.
                          </p>
                          {articleLink(row.url) && (
                            <a
                              href={articleLink(row.url) || undefined}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="mt-2 inline-block text-violet-300 hover:underline"
                            >
                              Read source article
                            </a>
                          )}
                        </AnimatedAccordion>
                        {labelling && row.status === 'eligible' && (
                          <label className="mt-3 block text-xs text-white/50">
                            Reference label for article {index + 1}
                            <AnimatedSelect
                              aria-label={`Reference label for article ${index + 1}`}
                              disabled={busy}
                              value={annotations[row.sample_id] || ''}
                              onValueChange={(nextValue) => {
                                const value = nextValue as
                                  ReferenceLabel | ''
                                const key = `${row.sample_id}:${row.text_sha256}`
                                if (
                                  value &&
                                  !draft.annotations[key] &&
                                  Object.keys(draft.annotations).length >= 500
                                ) {
                                  setError(
                                    'This local tone workspace holds 500 annotations. Export the local workspace and clear it before adding more.',
                                  )
                                  return
                                }
                                setValue((previous) => {
                                  const next = { ...previous.annotations }
                                  if (value)
                                    next[key] = {
                                      sample_id: row.sample_id,
                                      text_sha256: row.text_sha256,
                                      label: value,
                                    }
                                  else delete next[key]
                                  return { ...previous, annotations: next }
                                }, generation)
                              }}
                              className="mt-1 block w-full rounded-lg border border-white/10 bg-[#1d1d28] px-2 py-2 text-sm text-white"
                            >
                              <option value="">Unlabelled / uncertain</option>
                              <option value="negative">Negative</option>
                              <option value="neutral">Neutral</option>
                              <option value="positive">Positive</option>
                            </AnimatedSelect>
                          </label>
                        )}
                      </td>
                      {['vader', 'finsense', 'modernfinbert'].map((key) => (
                        <td key={key} className="p-3 align-top">
                          <Tone prediction={row.predictions[key]} />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="text-xs text-white/35">
            VADER score: compound −1…+1. Challenger score: positive minus
            negative softmax −1…+1, uncalibrated. Values are not directly
            comparable probabilities. Preview took{' '}
            {report.elapsed_ms.toFixed(0)} ms. Generated{' '}
            {valuationDate(report.generated_at)}.
          </p>
        </>
      )}
    </section>
  )
}
