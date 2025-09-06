export interface PublicVeteranProfile {
  profile_id: string;
  user_id: string;
  business_title: string;
  skills: {
    name: string;
    level: 'beginner' | 'intermediate' | 'advanced' | 'expert';
    years: number;
  }[];
  experiences: {
    title: string;
    department: string;
    duration: number;
    achievements: string[];
  }[];
  preferences: {
    preferred_roles: string[];
    work_style: 'remote' | 'hybrid' | 'onsite' | 'flexible';
    locations: string[];
    availability: 'full_time' | 'part_time' | 'consulting' | 'project_based';
  };
  summary: string;
  last_updated: string;
}

export interface SearchFilters {
  skills?: string[];
  experience_years?: {
    min: number;
    max: number;
  };
  locations?: string[];
  availability?: ('full_time' | 'part_time' | 'consulting' | 'project_based')[];
  work_style?: ('remote' | 'hybrid' | 'onsite' | 'flexible')[];
  preferred_roles?: string[];
}

export interface SearchResult {
  profiles: PublicVeteranProfile[];
  total_count: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface ContactRequest {
  contact_id: string;
  profile_id: string;
  recruiter_name: string;
  recruiter_email: string;
  company: string;
  position_title: string;
  message: string;
  status: 'sent' | 'viewed' | 'responded' | 'declined';
  sent_at: string;
  responded_at?: string;
}

export interface SkillCategory {
  category: string;
  skills: string[];
}