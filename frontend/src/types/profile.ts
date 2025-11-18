export interface Skill {
  name: string;
  level: 'beginner' | 'intermediate' | 'advanced' | 'expert';
  years: number;
  certifications: string[];
}

export interface Experience {
  title: string;
  department: string;
  duration: number;
  achievements: string[];
  description?: string;
}

export interface Preferences {
  preferred_roles: string[];
  work_style: 'remote' | 'hybrid' | 'onsite' | 'flexible';
  locations: string[];
  availability: 'full_time' | 'part_time' | 'consulting' | 'project_based';
}

export interface PrivacySettings {
  is_publicly_visible: boolean;
  external_contact: boolean;
  show_contact_info: boolean;
  show_detailed_experience: boolean;
}

export interface VeteranProfile {
  user_id: string;
  business_title: string;
  skills: Skill[];
  experiences: Experience[];
  preferences: Preferences;
  privacy_settings: PrivacySettings;
  questionnaire_responses: QuestionnaireResponse[];
  is_publicly_visible: string;
  last_updated: string;
}

export interface Question {
  id: string;
  text: string;
  type: 'text' | 'multiple_choice' | 'rating' | 'boolean';
  options?: string[];
  required: boolean;
  category: 'skills' | 'experience' | 'preferences' | 'goals';
}

export interface QuestionnaireResponse {
  question_id: string;
  answer: string | number | boolean;
  answered_at: string;
}

export interface Questionnaire {
  questionnaire_id: string;
  user_id: string;
  questions: Question[];
  responses: QuestionnaireResponse[];
  status: 'generated' | 'in_progress' | 'completed';
  generated_at: string;
  completed_at?: string;
}

export interface BusinessTitleSuggestion {
  title: string;
  reasoning: string;
  confidence_score: number;
}

export interface Opportunity {
  opportunity_id: string;
  title: string;
  description: string;
  required_skills: string[];
  location: string;
  type: 'internal_transfer' | 'external_position' | 'consulting' | 'project_based';
  source: 'internal' | 'external';
  company: string;
  salary_range: {
    min: number;
    max: number;
    currency: string;
  };
  is_active: boolean;
  posted_date: string;
  expiry_date: string;
}

export interface MatchReason {
  category: string;
  description: string;
  weight: number;
}

export interface Recommendation {
  user_id: string;
  recommendation_id: string;
  opportunity_id: string;
  opportunity: Opportunity;
  match_score: number;
  match_reasons: MatchReason[];
  status: 'generated' | 'viewed' | 'applied' | 'dismissed';
  generated_at: string;
  viewed_at?: string;
  applied_at?: string;
}

export interface Application {
  application_id: string;
  user_id: string;
  opportunity_id: string;
  opportunity: Opportunity;
  status: 'submitted' | 'under_review' | 'interview_scheduled' | 'accepted' | 'rejected' | 'withdrawn';
  applied_at: string;
  updated_at: string;
  notes?: string;
}

export interface UserStatistics {
  completed_questionnaires: number;
  received_recommendations: number;
  submitted_applications: number;
  profile_views: number;
}