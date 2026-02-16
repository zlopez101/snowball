import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import useCustomToast from "@/hooks/useCustomToast"
import { apiRequest } from "@/lib/api"

type TodayAction = {
  campaign_id: string
  campaign_title: string
  template_id: string
  target_id: string | null
  action_type: "call" | "email" | "boycott" | "event"
  title: string
  estimated_minutes: number
}

type TodayActionsResponse = {
  data: TodayAction[]
  count: number
}

type ActionStats = {
  window_days: number
  total_actions: number
  completed_actions: number
  skipped_actions: number
  calls: number
  emails: number
  boycotts: number
  events: number
  last_action_at: string | null
}

export const Route = createFileRoute("/_layout/actions")({
  component: Actions,
  head: () => ({
    meta: [
      {
        title: "Actions - Snowball",
      },
    ],
  }),
})

function Actions() {
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()

  const todayQuery = useQuery<TodayActionsResponse, Error>({
    queryKey: ["actions", "today"],
    queryFn: () => apiRequest<TodayActionsResponse>("/api/v1/actions/today"),
  })

  const statsQuery = useQuery<ActionStats, Error>({
    queryKey: ["actions", "stats", "7d"],
    queryFn: () => apiRequest<ActionStats>("/api/v1/actions/me/stats?window=7d"),
  })

  const logActionMutation = useMutation({
    mutationFn: async (action: TodayAction) => {
      const defaultOutcome = action.action_type === "email" ? "sent" : "answered"
      return apiRequest("/api/v1/actions/log", {
        method: "POST",
        body: JSON.stringify({
          campaign_id: action.campaign_id,
          template_id: action.template_id,
          target_id: action.target_id,
          action_type: action.action_type,
          status: "completed",
          outcome: defaultOutcome,
          confidence_score: 4,
        }),
      })
    },
    onSuccess: async () => {
      showSuccessToast("Action logged successfully")
      await queryClient.invalidateQueries({ queryKey: ["actions", "today"] })
      await queryClient.invalidateQueries({ queryKey: ["actions", "stats", "7d"] })
    },
    onError: (error: Error) => showErrorToast(error.message),
  })

  if (todayQuery.isLoading || statsQuery.isLoading) {
    return <p className="text-muted-foreground">Loading your action hub...</p>
  }

  if (todayQuery.error) {
    return <p className="text-destructive">{todayQuery.error.message}</p>
  }

  if (statsQuery.error) {
    return <p className="text-destructive">{statsQuery.error.message}</p>
  }

  const todayActions = todayQuery.data?.data || []
  const stats = statsQuery.data

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Today&apos;s Actions</h1>
        <p className="text-muted-foreground">
          Complete high-impact calls and emails, then log them here.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>7-Day Completed</CardDescription>
            <CardTitle>{stats?.completed_actions ?? 0}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Calls</CardDescription>
            <CardTitle>{stats?.calls ?? 0}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Emails</CardDescription>
            <CardTitle>{stats?.emails ?? 0}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div className="space-y-4">
        {todayActions.length === 0 ? (
          <Card>
            <CardHeader>
              <CardTitle>No actions scheduled for today</CardTitle>
              <CardDescription>
                Complete onboarding or update your daily plan to populate this list.
              </CardDescription>
            </CardHeader>
          </Card>
        ) : null}

        {todayActions.map((action) => (
          <Card key={action.template_id}>
            <CardHeader className="gap-3">
              <div className="flex items-center justify-between gap-3">
                <CardTitle className="text-lg">{action.title}</CardTitle>
                <Badge variant="secondary">{action.action_type.toUpperCase()}</Badge>
              </div>
              <CardDescription>{action.campaign_title}</CardDescription>
            </CardHeader>
            <CardContent className="flex items-center justify-between gap-3">
              <p className="text-sm text-muted-foreground">
                Estimated time: {action.estimated_minutes} min
              </p>
              <Button
                data-testid={`log-action-${action.template_id}`}
                onClick={() => logActionMutation.mutate(action)}
                disabled={logActionMutation.isPending}
              >
                Log Completed
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
