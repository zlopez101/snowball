import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { HttpError, apiRequest } from "@/lib/api"

type Campaign = {
  id: string
  title: string
}

type CampaignsResponse = {
  data: Campaign[]
  count: number
}

type Impact = {
  window_days: number
  total_actions: number
  completed_actions: number
  skipped_actions: number
  calls: number
  emails: number
  unique_participants: number
  participant_range: string
  campaign_id: string | null
  campaign_title: string | null
}

type ShareCard = {
  window_days: number
  shareable: boolean
  visibility_mode: "private" | "community" | "public_opt_in"
  display_name: string | null
  period_label: string
  total_actions: number
  completed_actions: number
  calls: number
  emails: number
  message: string
}

export const Route = createFileRoute("/_layout/impact")({
  component: ImpactPage,
  head: () => ({
    meta: [
      {
        title: "Impact - Snowball",
      },
    ],
  }),
})

function ImpactPage() {
  const campaignsQuery = useQuery<CampaignsResponse, Error>({
    queryKey: ["campaigns", "active"],
    queryFn: () => apiRequest<CampaignsResponse>("/api/v1/campaigns/?status=active"),
  })

  const firstCampaignId = campaignsQuery.data?.data[0]?.id
  const platformImpactQuery = useQuery<Impact, Error>({
    queryKey: ["impact", "platform", "7d"],
    queryFn: () => apiRequest<Impact>("/api/v1/impact/platform?window=7d"),
  })

  const campaignImpactQuery = useQuery<Impact, Error>({
    queryKey: ["impact", "campaign", firstCampaignId, "30d"],
    queryFn: () =>
      apiRequest<Impact>(`/api/v1/impact/campaign/${firstCampaignId}?window=30d`),
    enabled: !!firstCampaignId,
  })

  const shareCardQuery = useQuery<ShareCard | null, Error>({
    queryKey: ["impact", "share-card", "7d"],
    queryFn: async () => {
      try {
        return await apiRequest<ShareCard>("/api/v1/impact/me/share-card?window=7d")
      } catch (error) {
        if (error instanceof HttpError && error.status === 404) {
          return null
        }
        throw error
      }
    },
  })

  if (
    campaignsQuery.isLoading ||
    platformImpactQuery.isLoading ||
    campaignImpactQuery.isLoading ||
    shareCardQuery.isLoading
  ) {
    return <p className="text-muted-foreground">Loading impact metrics...</p>
  }

  if (campaignsQuery.error || platformImpactQuery.error || campaignImpactQuery.error) {
    return (
      <p className="text-destructive">
        {campaignsQuery.error?.message ||
          platformImpactQuery.error?.message ||
          campaignImpactQuery.error?.message}
      </p>
    )
  }

  const platform = platformImpactQuery.data
  const campaign = campaignImpactQuery.data
  const shareCard = shareCardQuery.data

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Impact Dashboard</h1>
        <p className="text-muted-foreground">
          Privacy-safe aggregate visibility for your campaigns and platform momentum.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card data-testid="impact-platform-total-card">
          <CardHeader>
            <CardDescription>Platform actions (7d)</CardDescription>
            <CardTitle>{platform?.total_actions ?? 0}</CardTitle>
          </CardHeader>
        </Card>
        <Card data-testid="impact-platform-participants-card">
          <CardHeader>
            <CardDescription>Participants range</CardDescription>
            <CardTitle>{platform?.participant_range ?? "0"}</CardTitle>
          </CardHeader>
        </Card>
        <Card data-testid="impact-campaign-completed-card">
          <CardHeader>
            <CardDescription>
              Campaign completed (30d)
              {campaign?.campaign_title ? `: ${campaign.campaign_title}` : ""}
            </CardDescription>
            <CardTitle>{campaign?.completed_actions ?? 0}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card data-testid="impact-share-card">
        <CardHeader>
          <CardTitle>Share Card Preview</CardTitle>
          <CardDescription>Only opt-in details are shown by default.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {shareCard ? (
            <>
              <p>
                <span className="font-medium">Period:</span> {shareCard.period_label}
              </p>
              <p>
                <span className="font-medium">Completed actions:</span>{" "}
                {shareCard.completed_actions}
              </p>
              <p>
                <span className="font-medium">Calls / Emails:</span> {shareCard.calls} /{" "}
                {shareCard.emails}
              </p>
              <p>
                <span className="font-medium">Display name:</span>{" "}
                <span data-testid="share-card-display-name">
                  {shareCard.display_name || "Hidden"}
                </span>
              </p>
              <p data-testid="share-card-message" className="text-muted-foreground">
                {shareCard.message}
              </p>
            </>
          ) : (
            <p className="text-muted-foreground">
              Complete onboarding to generate your share card preview.
            </p>
          )}
          {!shareCard?.shareable ? (
            <Button asChild size="sm" variant="outline">
              <Link to="/settings">Enable in Privacy Settings</Link>
            </Button>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
