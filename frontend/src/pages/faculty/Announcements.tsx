import { AnnouncementFeed } from '@/components/announcements/AnnouncementFeed'

export default function FacultyAnnouncements() {
  return (
    <AnnouncementFeed
      queryKey="faculty-announcements"
      canManage
      subtitle="Publish notices to departments, courses, or faculty"
    />
  )
}
