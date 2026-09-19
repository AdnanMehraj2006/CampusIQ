import { AnnouncementFeed } from '@/components/announcements/AnnouncementFeed'

export default function HODAnnouncements() {
  return (
    <AnnouncementFeed
      queryKey="hod-announcements"
      canManage
      subtitle="Publish notices to your department, courses, sections or faculty"
    />
  )
}
