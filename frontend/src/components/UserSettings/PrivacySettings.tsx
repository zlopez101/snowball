import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { Checkbox } from "@/components/ui/checkbox"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"
import { apiRequest } from "@/lib/api"

type PrivacySettings = {
  user_id: string
  show_on_leaderboard: boolean
  show_streaks: boolean
  show_badges: boolean
  allow_shareable_card: boolean
  allow_referral_tracking: boolean
}

type ProfileSettings = {
  user_id: string
  visibility_mode: "private" | "community" | "public_opt_in"
}

const PrivacySettings = () => {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const privacyQuery = useQuery<PrivacySettings, Error>({
    queryKey: ["privacy", "me"],
    queryFn: () => apiRequest<PrivacySettings>("/api/v1/privacy/me"),
  })

  const profileQuery = useQuery<ProfileSettings, Error>({
    queryKey: ["profile", "me"],
    queryFn: () => apiRequest<ProfileSettings>("/api/v1/profile/me"),
  })

  const mutation = useMutation({
    mutationFn: (payload: Partial<PrivacySettings>) =>
      apiRequest<PrivacySettings>("/api/v1/privacy/me", {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: async () => {
      showSuccessToast("Privacy settings updated")
      await queryClient.invalidateQueries({ queryKey: ["privacy", "me"] })
    },
    onError: (error: Error) => showErrorToast(error.message),
  })

  const visibilityMutation = useMutation({
    mutationFn: (visibilityMode: ProfileSettings["visibility_mode"]) =>
      apiRequest<ProfileSettings>("/api/v1/profile/me", {
        method: "PATCH",
        body: JSON.stringify({ visibility_mode: visibilityMode }),
      }),
    onSuccess: async () => {
      showSuccessToast("Visibility mode updated")
      await queryClient.invalidateQueries({ queryKey: ["profile", "me"] })
    },
    onError: (error: Error) => showErrorToast(error.message),
  })

  if (privacyQuery.isLoading || profileQuery.isLoading) {
    return <p className="text-muted-foreground">Loading privacy settings...</p>
  }

  if (privacyQuery.error || !privacyQuery.data || profileQuery.error || !profileQuery.data) {
    return (
      <p className="text-destructive">
        {privacyQuery.error?.message ||
          profileQuery.error?.message ||
          "Unable to load privacy settings"}
      </p>
    )
  }

  const settings = privacyQuery.data
  const profile = profileQuery.data

  const toggle = (key: keyof Omit<PrivacySettings, "user_id">, value: boolean) => {
    mutation.mutate({ [key]: value })
  }

  return (
    <div className="max-w-xl space-y-5">
      <div>
        <h3 className="text-lg font-semibold py-4">Privacy Controls</h3>
        <p className="text-sm text-muted-foreground">
          Snowball defaults to private participation. You can opt into limited visibility below.
        </p>
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium">Visibility mode</p>
        <Select
          value={profile.visibility_mode}
          onValueChange={(value) =>
            visibilityMutation.mutate(value as ProfileSettings["visibility_mode"])
          }
        >
          <SelectTrigger className="w-full" data-testid="privacy-visibility-select">
            <SelectValue placeholder="Select visibility mode" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="private">Private</SelectItem>
            <SelectItem value="community">Community</SelectItem>
            <SelectItem value="public_opt_in">Public (opt-in)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-4">
        <label className="flex items-center gap-3">
          <Checkbox
            data-testid="privacy-show-on-leaderboard"
            checked={settings.show_on_leaderboard}
            onCheckedChange={(value) => toggle("show_on_leaderboard", value === true)}
          />
          <span>Show me on leaderboard</span>
        </label>

        <label className="flex items-center gap-3">
          <Checkbox
            data-testid="privacy-show-streaks"
            checked={settings.show_streaks}
            onCheckedChange={(value) => toggle("show_streaks", value === true)}
          />
          <span>Show my streaks</span>
        </label>

        <label className="flex items-center gap-3">
          <Checkbox
            data-testid="privacy-show-badges"
            checked={settings.show_badges}
            onCheckedChange={(value) => toggle("show_badges", value === true)}
          />
          <span>Show my badges</span>
        </label>

        <label className="flex items-center gap-3">
          <Checkbox
            data-testid="privacy-shareable-card"
            checked={settings.allow_shareable_card}
            onCheckedChange={(value) => toggle("allow_shareable_card", value === true)}
          />
          <span>Allow shareable impact card</span>
        </label>

        <label className="flex items-center gap-3">
          <Checkbox
            data-testid="privacy-referral-tracking"
            checked={settings.allow_referral_tracking}
            onCheckedChange={(value) =>
              toggle("allow_referral_tracking", value === true)
            }
          />
          <span>Enable referral tracking</span>
        </label>
      </div>

      <p className="text-sm text-muted-foreground">
        {mutation.isPending || visibilityMutation.isPending
          ? "Saving..."
          : "Changes are saved automatically."}
      </p>
    </div>
  )
}

export default PrivacySettings
