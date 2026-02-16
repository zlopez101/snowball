import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"
import useAuth from "@/hooks/useAuth"
import { HttpError, apiRequest } from "@/lib/api"

type Campaign = {
  id: string
  title: string
}

type CampaignsResponse = {
  data: Campaign[]
  count: number
}

type UserProfile = {
  user_id: string
  username: string
  state_code: string | null
  district_code: string | null
  timezone: string
  visibility_mode: string
}

const weekdayOptions = [
  { key: "mon", label: "Mon" },
  { key: "tue", label: "Tue" },
  { key: "wed", label: "Wed" },
  { key: "thu", label: "Thu" },
  { key: "fri", label: "Fri" },
  { key: "sat", label: "Sat" },
  { key: "sun", label: "Sun" },
] as const

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "Dashboard - FastAPI Template",
      },
    ],
  }),
})

function Dashboard() {
  const { user: currentUser } = useAuth()
  const queryClient = useQueryClient()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const [username, setUsername] = useState("")
  const [stateCode, setStateCode] = useState("TX")
  const [districtCode, setDistrictCode] = useState("01")
  const [selectedCampaignIds, setSelectedCampaignIds] = useState<string[]>([])
  const [targetActionsPerDay, setTargetActionsPerDay] = useState("3")
  const [weekdayMask, setWeekdayMask] = useState<boolean[]>([
    true,
    true,
    true,
    true,
    true,
    false,
    false,
  ])

  const profileQuery = useQuery<UserProfile | null, Error>({
    queryKey: ["profile", "me"],
    queryFn: async () => {
      try {
        return await apiRequest<UserProfile>("/api/v1/profile/me")
      } catch (error) {
        if (error instanceof HttpError && error.status === 404) {
          return null
        }
        throw error
      }
    },
  })

  const campaignsQuery = useQuery<CampaignsResponse, Error>({
    queryKey: ["campaigns", "active"],
    queryFn: () => apiRequest<CampaignsResponse>("/api/v1/campaigns/?status=active"),
  })

  useEffect(() => {
    if (!campaignsQuery.data?.data.length || selectedCampaignIds.length > 0) {
      return
    }
    setSelectedCampaignIds([campaignsQuery.data.data[0].id])
  }, [campaignsQuery.data, selectedCampaignIds.length])

  const onboardingMutation = useMutation({
    mutationFn: async () => {
      if (!username.trim()) {
        throw new Error("Username is required")
      }
      if (selectedCampaignIds.length === 0) {
        throw new Error("Select at least one campaign")
      }
      const activeWeekdaysMask = weekdayMask.map((value) => (value ? "1" : "0")).join("")
      return apiRequest("/api/v1/onboarding/complete", {
        method: "POST",
        body: JSON.stringify({
          username: username.trim(),
          state_code: stateCode.trim() || null,
          district_code: districtCode.trim() || null,
          timezone: "America/Chicago",
          visibility_mode: "private",
          campaign_ids: selectedCampaignIds,
          target_actions_per_day: Number(targetActionsPerDay),
          active_weekdays_mask: activeWeekdaysMask,
        }),
      })
    },
    onSuccess: async () => {
      showSuccessToast("Onboarding completed")
      await queryClient.invalidateQueries({ queryKey: ["profile", "me"] })
      await queryClient.invalidateQueries({ queryKey: ["actions", "today"] })
    },
    onError: (error: Error) => showErrorToast(error.message),
  })

  const toggleCampaign = (campaignId: string, checked: boolean) => {
    if (checked) {
      setSelectedCampaignIds((current) => [...new Set([...current, campaignId])])
      return
    }
    setSelectedCampaignIds((current) => current.filter((id) => id !== campaignId))
  }

  const toggleWeekday = (index: number, checked: boolean) => {
    setWeekdayMask((current) => {
      const next = [...current]
      next[index] = checked
      return next
    })
  }

  if (profileQuery.isLoading || campaignsQuery.isLoading) {
    return <p className="text-muted-foreground">Loading your Snowball dashboard...</p>
  }

  if (profileQuery.error) {
    return <p className="text-destructive">{profileQuery.error.message}</p>
  }

  if (campaignsQuery.error) {
    return <p className="text-destructive">{campaignsQuery.error.message}</p>
  }

  if (!profileQuery.data) {
    return (
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Complete your onboarding</CardTitle>
          <CardDescription>
            Set your profile and daily action plan to unlock today&apos;s action list.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="username">
              Username
            </label>
            <Input
              data-testid="onboarding-username-input"
              id="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="snowball_organizer"
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="state">
                State Code
              </label>
              <Input
                data-testid="onboarding-state-input"
                id="state"
                value={stateCode}
                maxLength={2}
                onChange={(event) => setStateCode(event.target.value.toUpperCase())}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="district">
                District
              </label>
              <Input
                data-testid="onboarding-district-input"
                id="district"
                value={districtCode}
                onChange={(event) => setDistrictCode(event.target.value)}
              />
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Campaigns</label>
            <div className="space-y-2">
              {campaignsQuery.data?.data.map((campaign) => (
                <label key={campaign.id} className="flex items-center gap-3">
                  <Checkbox
                    data-testid={`onboarding-campaign-${campaign.id}`}
                    checked={selectedCampaignIds.includes(campaign.id)}
                    onCheckedChange={(value) =>
                      toggleCampaign(campaign.id, value === true)
                    }
                  />
                  <span className="text-sm">{campaign.title}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Daily target actions</label>
              <Select
                value={targetActionsPerDay}
                onValueChange={(value) => setTargetActionsPerDay(value)}
              >
                <SelectTrigger className="w-full" data-testid="onboarding-target-select">
                  <SelectValue placeholder="Select target" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1 action/day</SelectItem>
                  <SelectItem value="2">2 actions/day</SelectItem>
                  <SelectItem value="3">3 actions/day</SelectItem>
                  <SelectItem value="4">4 actions/day</SelectItem>
                  <SelectItem value="5">5 actions/day</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Active days</label>
              <div className="flex flex-wrap gap-3">
                {weekdayOptions.map((weekday, index) => (
                  <label key={weekday.key} className="flex items-center gap-2">
                    <Checkbox
                      data-testid={`onboarding-weekday-${weekday.key}`}
                      checked={weekdayMask[index]}
                      onCheckedChange={(value) =>
                        toggleWeekday(index, value === true)
                      }
                    />
                    <span className="text-xs">{weekday.label}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
          <Button
            data-testid="onboarding-submit"
            onClick={() => onboardingMutation.mutate()}
            disabled={onboardingMutation.isPending}
          >
            {onboardingMutation.isPending ? "Saving..." : "Finish onboarding"}
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl truncate max-w-sm font-semibold">
          Hi, {currentUser?.full_name || currentUser?.email} 👋
        </h1>
        <p className="text-muted-foreground">Ready for today&apos;s civic actions.</p>
      </div>
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Profile Summary</CardTitle>
          <CardDescription>Current onboarding and visibility configuration.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>
            <span className="font-medium">Username:</span> {profileQuery.data.username}
          </p>
          <p>
            <span className="font-medium">State:</span> {profileQuery.data.state_code || "N/A"}
          </p>
          <p>
            <span className="font-medium">District:</span>{" "}
            {profileQuery.data.district_code || "N/A"}
          </p>
          <p>
            <span className="font-medium">Visibility:</span> {profileQuery.data.visibility_mode}
          </p>
        </CardContent>
      </Card>
      <Button asChild>
        <Link to="/actions">Go To Today&apos;s Actions</Link>
      </Button>
    </div>
  )
}
