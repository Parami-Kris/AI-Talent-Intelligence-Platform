import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from './client'
import { parseUpload, resumePipeline, runPipeline } from './endpoints'

function jsonResponse(body: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    statusText: 'error',
    json: async () => body,
  } as Response
}

describe('api endpoints', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('parseUpload posts a multipart FormData request', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValue(jsonResponse({ jd: {}, candidates: [], failures: [] }))

    const jdFile = new File(['jd text'], 'jd.txt', { type: 'text/plain' })
    const resumeFile = new File(['resume text'], 'resume.txt', { type: 'text/plain' })
    await parseUpload(jdFile, [resumeFile])

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url)).toContain('/upload/parse')
    expect(init?.method).toBe('POST')
    expect(init?.body).toBeInstanceOf(FormData)
  })

  it('runPipeline posts a JSON request', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValue(
      jsonResponse({ thread_id: 't1', status: 'no_eligible_candidates', batch_ranking: null, review_payload: null }),
    )

    await runPipeline({ jd: {}, candidates: [], run_name: 'run', source_file: 'jd.txt', top_n: 10 })

    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url)).toContain('/pipeline/run')
    expect(init?.method).toBe('POST')
    expect(init?.headers).toEqual({ 'Content-Type': 'application/json' })
    expect(JSON.parse(init?.body as string)).toMatchObject({ run_name: 'run', top_n: 10 })
  })

  it('throws ApiError with the response detail on a non-2xx response', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'thread not found' }, false, 404))

    await expect(resumePipeline({ thread_id: 'missing', action: 'approve' })).rejects.toMatchObject(
      new ApiError(404, 'thread not found'),
    )
  })

  it('normalizes a network failure into an ApiError', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(runPipeline({ jd: {}, candidates: [], run_name: 'r', source_file: 'f', top_n: 1 })).rejects.toThrow(
      ApiError,
    )
  })
})
