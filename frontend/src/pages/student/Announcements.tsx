import { AnnouncementFeed } from '@/components/announcements/AnnouncementFeed'

export default function StudentAnnouncements() {
  return (
    <AnnouncementFeed
      queryKey="student-announcements"
      canManage={false}
      subtitle="Stay up to date with notices relevant to you"
    />
  )
}
