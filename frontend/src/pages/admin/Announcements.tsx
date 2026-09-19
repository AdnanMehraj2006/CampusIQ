import { AnnouncementFeed } from '@/components/announcements/AnnouncementFeed'

export default function AdminAnnouncements() {
  return (
    <AnnouncementFeed
      queryKey="admin-announcements"
      canManage
      subtitle="Publish and manage announcements across the institution"
    />
  )
}
