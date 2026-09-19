import { AnnouncementFeed } from '@/components/announcements/AnnouncementFeed'

export default function CRAnnouncements() {
  return (
    <AnnouncementFeed
      queryKey="cr-announcements"
      canManage={false}
      subtitle="Notices for your class and section"
    />
  )
}
