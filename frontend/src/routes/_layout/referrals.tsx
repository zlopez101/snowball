import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import useCustomToast from "@/hooks/useCustomToast"
import { apiRequest } from "@/lib/api"

type Referral = {
  id: string
  referrer_user_id: string
  referred_user_id: string | null
  code: string
  channel: "link" | "qr" | "social"
  invite_url: string
  created_at: string | null
}

type ReferralsResponse = {
  data: Referral[]
  count: number
}

type ReferralAssistStats = {
  window_days: number
  recruited_users: number
  assisted_actions: number
}

type Message = {
  message: string
}

export const Route = createFileRoute("/_layout/referrals")({
  component: ReferralsPage,
  head: () => ({
    meta: [
      {
        title: "Referrals - Snowball",
      },
    ],
  }),
})

function ReferralsPage() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [claimCode, setClaimCode] = useState("")

  const referralsQuery = useQuery<ReferralsResponse, Error>({
    queryKey: ["referrals", "me"],
    queryFn: () => apiRequest<ReferralsResponse>("/api/v1/referrals/me"),
  })

  const assistsQuery = useQuery<ReferralAssistStats, Error>({
    queryKey: ["referrals", "assists", "7d"],
    queryFn: () => apiRequest<ReferralAssistStats>("/api/v1/referrals/me/assists?window=7d"),
  })

  const createLinkMutation = useMutation({
    mutationFn: async () =>
      apiRequest<Referral>("/api/v1/referrals/link", {
        method: "POST",
        body: JSON.stringify({ channel: "link" }),
      }),
    onSuccess: async () => {
      showSuccessToast("Referral link created")
      await queryClient.invalidateQueries({ queryKey: ["referrals", "me"] })
      await queryClient.invalidateQueries({ queryKey: ["referrals", "assists", "7d"] })
    },
    onError: (error: Error) => showErrorToast(error.message),
  })

  const claimMutation = useMutation({
    mutationFn: async (code: string) =>
      apiRequest<Message>("/api/v1/referrals/claim", {
        method: "POST",
        body: JSON.stringify({ code }),
      }),
    onSuccess: async () => {
      showSuccessToast("Referral claimed")
      setClaimCode("")
      await queryClient.invalidateQueries({ queryKey: ["referrals", "me"] })
      await queryClient.invalidateQueries({ queryKey: ["referrals", "assists", "7d"] })
    },
    onError: (error: Error) => showErrorToast(error.message),
  })

  if (referralsQuery.isLoading || assistsQuery.isLoading) {
    return <p className="text-muted-foreground">Loading referral metrics...</p>
  }

  if (referralsQuery.error || assistsQuery.error) {
    return (
      <p className="text-destructive">
        {referralsQuery.error?.message || assistsQuery.error?.message}
      </p>
    )
  }

  const referrals = referralsQuery.data?.data ?? []
  const latestLink = referrals[0]
  const assists = assistsQuery.data

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Referrals</h1>
        <p className="text-muted-foreground">
          Invite people into the action loop and track assists from recruited participants.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardDescription>Recruited users (7d)</CardDescription>
            <CardTitle data-testid="recruited-users-value">
              {assists?.recruited_users ?? 0}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Assisted actions (7d)</CardDescription>
            <CardTitle data-testid="assisted-actions-value">
              {assists?.assisted_actions ?? 0}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Create invite link</CardTitle>
          <CardDescription>Generate a unique link for new users to join Snowball.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button
            data-testid="create-referral-link"
            onClick={() => createLinkMutation.mutate()}
            disabled={createLinkMutation.isPending}
          >
            {createLinkMutation.isPending ? "Creating..." : "Generate Referral Link"}
          </Button>
          {latestLink ? (
            <div className="space-y-1 text-sm">
              <p>
                <span className="font-medium">Code:</span>{" "}
                <span data-testid="latest-referral-code">{latestLink.code}</span>
              </p>
              <p>
                <span className="font-medium">Invite URL:</span>{" "}
                <span data-testid="latest-referral-url">{latestLink.invite_url}</span>
              </p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No links generated yet.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Claim referral code</CardTitle>
          <CardDescription>Use this if someone shared a code with you directly.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col md:flex-row gap-3">
          <Input
            data-testid="claim-referral-code-input"
            value={claimCode}
            onChange={(event) => setClaimCode(event.target.value)}
            placeholder="Enter referral code"
          />
          <Button
            data-testid="claim-referral-code-button"
            onClick={() => claimMutation.mutate(claimCode.trim())}
            disabled={claimMutation.isPending || claimCode.trim().length < 6}
          >
            {claimMutation.isPending ? "Claiming..." : "Claim Code"}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
