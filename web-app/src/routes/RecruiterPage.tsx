import { useState } from 'react'
import type {
  BatchRankingResult,
  PersistenceResult,
  PipelineResumeResponse,
  PipelineRunResponse,
  RerankedResult,
  ReviewPayload,
} from '../api/types'
import { NoEligibleStep, ResultStep } from '../features/recruiter/ResultStep'
import { ReviewStep } from '../features/recruiter/ReviewStep'
import { UploadStep } from '../features/recruiter/UploadStep'

type RecruiterState =
  | { step: 'upload' }
  | { step: 'no_eligible'; batchRanking: BatchRankingResult }
  | { step: 'review'; threadId: string; batchRanking: BatchRankingResult; reviewPayload: ReviewPayload }
  | {
      step: 'result'
      status: 'persisted' | 'rejected'
      reranked: RerankedResult | null
      persistenceResult: PersistenceResult | null
    }

export function RecruiterPage() {
  const [state, setState] = useState<RecruiterState>({ step: 'upload' })

  const handlePipelineRun = (result: PipelineRunResponse) => {
    if (result.status === 'awaiting_review' && result.batch_ranking && result.review_payload) {
      setState({
        step: 'review',
        threadId: result.thread_id,
        batchRanking: result.batch_ranking,
        reviewPayload: result.review_payload,
      })
    } else if (result.batch_ranking) {
      setState({ step: 'no_eligible', batchRanking: result.batch_ranking })
    }
  }

  const handleResumed = (result: PipelineResumeResponse) => {
    setState({
      step: 'result',
      status: result.status,
      reranked: result.reranked,
      persistenceResult: result.persistence_result,
    })
  }

  const startNew = () => setState({ step: 'upload' })

  switch (state.step) {
    case 'upload':
      return <UploadStep onPipelineRun={handlePipelineRun} />
    case 'no_eligible':
      return <NoEligibleStep batchRanking={state.batchRanking} onStartNew={startNew} />
    case 'review':
      return (
        <ReviewStep
          threadId={state.threadId}
          batchRanking={state.batchRanking}
          reviewPayload={state.reviewPayload}
          onResumed={handleResumed}
        />
      )
    case 'result':
      return (
        <ResultStep
          status={state.status}
          reranked={state.reranked}
          persistenceResult={state.persistenceResult}
          onStartNew={startNew}
        />
      )
  }
}
