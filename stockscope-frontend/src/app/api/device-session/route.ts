import { NextRequest, NextResponse } from 'next/server'

const endpoint = '/api/device-session'
const cookie = 'stockscope_device'
const backend = (process.env.STOCKSCOPE_INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
const actions = new Set(['sign-in', 'setup', 'accept-invite', 'resume', 'forget'])

function json(body: unknown, status = 200) {
  return NextResponse.json(body, { status, headers: { 'Cache-Control': 'private, no-store' } })
}

function deviceCookie(response: NextResponse, request: NextRequest, value: string, maxAge: number) {
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(request.nextUrl.hostname)
  response.cookies.set(cookie, value, {
    path: endpoint, maxAge, httpOnly: true, sameSite: 'strict',
    secure: !local || request.nextUrl.protocol === 'https:',
  })
  return response
}

export async function POST(request: NextRequest) {
  // Only our same-origin client sends this custom header. No CORS opt-in.
  if (request.headers.get('X-StockScope-Device') !== '1' ||
      ['cross-site', 'same-site'].includes(request.headers.get('Sec-Fetch-Site') || '')) {
    return json({ detail: 'Use the StockScope sign-in form.' }, 403)
  }
  const input = await request.json().catch(() => null)
  if (!input || !actions.has(input.action)) return json({ detail: 'Unknown sign-in action.' }, 400)
  if (input.action === 'forget') return deviceCookie(json({}), request, '', 0)
  const resume = input.action === 'resume'
  const token = request.cookies.get(cookie)?.value
  if (resume && !token) return json({ detail: 'Sign in to continue.' }, 401)
  try {
    const upstream = await fetch(backend + '/api/auth/' + input.action, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(resume ? { token } : input.credentials),
      redirect: 'error', cache: 'no-store', signal: AbortSignal.timeout(20000),
    })
    const body = await upstream.json()
    // The long-lived credential is only returned to the device as an HttpOnly cookie.
    const { device_token: deviceToken, device_max_age: maxAge, ...publicBody } = body
    const result = upstream.ok ? json(publicBody, upstream.status) : json({
      detail: typeof body.detail === 'string' ? body.detail : 'Please check your sign-in details.',
    }, upstream.status)
    // A late resume response must never overwrite a newer sign-in cookie.
    if (!upstream.ok || resume) return result
    const remember = typeof deviceToken === 'string' && Number.isInteger(maxAge) && maxAge > 0
    result.headers.set('X-StockScope-Remembered', remember ? '1' : '0')
    return deviceCookie(result, request, remember ? deviceToken : '', remember ? maxAge : 0)
  } catch {
    return json({ detail: 'The workspace is temporarily unavailable. Please retry.' }, 503)
  }
}
