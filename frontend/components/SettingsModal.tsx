'use client';

import { useState, useEffect } from 'react';
import { X, User, MessageCircle, Briefcase, Shield, Save } from 'lucide-react';

interface UserSettings {
  // User Profile
  fullName: string;
  jobTitle: string;
  department: string;
  securityClearance: string;
  preferredLanguage: string;
  experienceLevel: string;

  // AI Response Customization
  communicationStyle: string;
  detailLevel: string;
  responseFormat: string;
  technicalLevel: string;
  urgencyPreference: string;

  // Workflow Preferences
  defaultContentTypes: string[];
  notificationSettings: string[];
  autoSavePreference: string;
  exportFormats: string[];

  // Department-Specific
  focusAreas: string[];
  stakeholderGroups: string[];
  complianceRequirements: string[];
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

const defaultSettings: UserSettings = {
  fullName: '',
  jobTitle: '',
  department: '',
  securityClearance: 'standard',
  preferredLanguage: 'english',
  experienceLevel: 'intermediate',
  communicationStyle: 'professional',
  detailLevel: 'comprehensive',
  responseFormat: 'structured',
  technicalLevel: 'balanced',
  urgencyPreference: 'thorough',
  defaultContentTypes: ['summary', 'slides'],
  notificationSettings: ['content-ready'],
  autoSavePreference: '30-days',
  exportFormats: ['pdf', 'word'],
  focusAreas: [],
  stakeholderGroups: [],
  complianceRequirements: []
};

export default function SettingsModal({ isOpen, onClose }: Props) {
  const [settings, setSettings] = useState<UserSettings>(defaultSettings);
  const [activeTab, setActiveTab] = useState<'profile' | 'ai' | 'workflow' | 'department'>('profile');
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    // Load settings from localStorage
    const savedSettings = localStorage.getItem('userSettings');
    if (savedSettings) {
      setSettings(JSON.parse(savedSettings));
    }
  }, []);

  const handleSettingChange = (key: keyof UserSettings, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const handleArrayChange = (key: keyof UserSettings, value: string, checked: boolean) => {
    const currentArray = settings[key] as string[];
    const newArray = checked
      ? [...currentArray, value]
      : currentArray.filter(item => item !== value);

    handleSettingChange(key, newArray);
  };

  const saveSettings = () => {
    localStorage.setItem('userSettings', JSON.stringify(settings));
    setHasChanges(false);
    // Here you would also send to backend API
    // await axios.put('/api/user/settings', settings);
  };

  const resetSettings = () => {
    setSettings(defaultSettings);
    setHasChanges(true);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 sm:p-6 border-b border-neutral-200">
          <h2 className="text-xl sm:text-2xl font-bold text-neutral-900">Settings</h2>
          <button
            onClick={onClose}
            className="text-neutral-500 hover:text-neutral-700 p-2 hover:bg-neutral-100 rounded-lg"
          >
            <X className="w-5 h-5 sm:w-6 sm:h-6" />
          </button>
        </div>

        {/* Mobile Tab Navigation */}
        <div className="sm:hidden border-b border-neutral-200 bg-neutral-50">
          <div className="flex overflow-x-auto scrollbar-custom">
            <button
              onClick={() => setActiveTab('profile')}
              className={`flex items-center gap-2 px-4 py-3 whitespace-nowrap text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'profile'
                  ? 'border-primary-500 text-primary-700 bg-primary-50'
                  : 'border-transparent text-neutral-600 hover:text-neutral-900'
              }`}
            >
              <User className="w-4 h-4" />
              Profile
            </button>
            <button
              onClick={() => setActiveTab('ai')}
              className={`flex items-center gap-2 px-4 py-3 whitespace-nowrap text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'ai'
                  ? 'border-primary-500 text-primary-700 bg-primary-50'
                  : 'border-transparent text-neutral-600 hover:text-neutral-900'
              }`}
            >
              <MessageCircle className="w-4 h-4" />
              AI
            </button>
            <button
              onClick={() => setActiveTab('workflow')}
              className={`flex items-center gap-2 px-4 py-3 whitespace-nowrap text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'workflow'
                  ? 'border-primary-500 text-primary-700 bg-primary-50'
                  : 'border-transparent text-neutral-600 hover:text-neutral-900'
              }`}
            >
              <Briefcase className="w-4 h-4" />
              Workflow
            </button>
            <button
              onClick={() => setActiveTab('department')}
              className={`flex items-center gap-2 px-4 py-3 whitespace-nowrap text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'department'
                  ? 'border-primary-500 text-primary-700 bg-primary-50'
                  : 'border-transparent text-neutral-600 hover:text-neutral-900'
              }`}
            >
              <Shield className="w-4 h-4" />
              Department
            </button>
          </div>
        </div>

        <div className="flex h-[500px] sm:h-[600px]">
          {/* Desktop Sidebar */}
          <div className="hidden sm:block w-1/4 bg-neutral-50 border-r border-neutral-200 p-4">
            <nav className="space-y-2">
              <button
                onClick={() => setActiveTab('profile')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors ${
                  activeTab === 'profile'
                    ? 'bg-primary-100 text-primary-700 font-medium'
                    : 'text-neutral-600 hover:bg-neutral-100'
                }`}
              >
                <User className="w-5 h-5" />
                User Profile
              </button>
              <button
                onClick={() => setActiveTab('ai')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors ${
                  activeTab === 'ai'
                    ? 'bg-primary-100 text-primary-700 font-medium'
                    : 'text-neutral-600 hover:bg-neutral-100'
                }`}
              >
                <MessageCircle className="w-5 h-5" />
                AI Responses
              </button>
              <button
                onClick={() => setActiveTab('workflow')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors ${
                  activeTab === 'workflow'
                    ? 'bg-primary-100 text-primary-700 font-medium'
                    : 'text-neutral-600 hover:bg-neutral-100'
                }`}
              >
                <Briefcase className="w-5 h-5" />
                Workflow
              </button>
              <button
                onClick={() => setActiveTab('department')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors ${
                  activeTab === 'department'
                    ? 'bg-primary-100 text-primary-700 font-medium'
                    : 'text-neutral-600 hover:bg-neutral-100'
                }`}
              >
                <Shield className="w-5 h-5" />
                Department
              </button>
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1 p-4 sm:p-6 overflow-y-auto">
            {activeTab === 'profile' && (
              <div className="space-y-4 sm:space-y-6">
                <h3 className="text-base sm:text-lg font-semibold text-neutral-900 mb-3 sm:mb-4">User Profile Settings</h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                  <div>
                    <label className="block text-xs sm:text-sm font-medium text-neutral-700 mb-2">Full Name</label>
                    <input
                      type="text"
                      value={settings.fullName}
                      onChange={(e) => handleSettingChange('fullName', e.target.value)}
                      className="input text-sm"
                      placeholder="Enter your full name"
                    />
                  </div>
                  <div>
                    <label className="block text-xs sm:text-sm font-medium text-neutral-700 mb-2">Job Title</label>
                    <input
                      type="text"
                      value={settings.jobTitle}
                      onChange={(e) => handleSettingChange('jobTitle', e.target.value)}
                      className="input text-sm"
                      placeholder="e.g., Senior Analyst"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs sm:text-sm font-medium text-neutral-700 mb-2">Department</label>
                  <select
                    value={settings.department}
                    onChange={(e) => handleSettingChange('department', e.target.value)}
                    className="input text-sm"
                  >
                    <option value="">Select Department</option>
                    <option value="immigration">Immigration Affairs</option>
                    <option value="citizenship">Citizenship & Residency</option>
                    <option value="customs">Customs</option>
                    <option value="ports-security">Ports Security</option>
                    <option value="border-control">Border Control</option>
                    <option value="intelligence">Intelligence & Analysis</option>
                    <option value="administration">Administration</option>
                  </select>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                  <div>
                    <label className="block text-xs sm:text-sm font-medium text-neutral-700 mb-2">Security Clearance</label>
                    <select
                      value={settings.securityClearance}
                      onChange={(e) => handleSettingChange('securityClearance', e.target.value)}
                      className="input text-sm"
                    >
                      <option value="standard">Standard</option>
                      <option value="confidential">Confidential</option>
                      <option value="secret">Secret</option>
                      <option value="top-secret">Top Secret</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs sm:text-sm font-medium text-neutral-700 mb-2">Preferred Language</label>
                    <select
                      value={settings.preferredLanguage}
                      onChange={(e) => handleSettingChange('preferredLanguage', e.target.value)}
                      className="input text-sm"
                    >
                      <option value="english">English</option>
                      <option value="arabic">العربية</option>
                      <option value="both">Both Languages</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs sm:text-sm font-medium text-neutral-700 mb-2">Experience Level</label>
                  <select
                    value={settings.experienceLevel}
                    onChange={(e) => handleSettingChange('experienceLevel', e.target.value)}
                    className="input text-sm"
                  >
                    <option value="beginner">Beginner (0-2 years)</option>
                    <option value="intermediate">Intermediate (3-7 years)</option>
                    <option value="senior">Senior (8-15 years)</option>
                    <option value="expert">Expert (15+ years)</option>
                  </select>
                </div>
              </div>
            )}

            {activeTab === 'ai' && (
              <div className="space-y-4 sm:space-y-6">
                <h3 className="text-base sm:text-lg font-semibold text-neutral-900 mb-3 sm:mb-4">AI Response Customization</h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                  <div>
                    <label className="block text-xs sm:text-sm font-medium text-neutral-700 mb-2">Communication Style</label>
                    <select
                      value={settings.communicationStyle}
                      onChange={(e) => handleSettingChange('communicationStyle', e.target.value)}
                      className="input text-sm"
                    >
                      <option value="formal">Formal & Official</option>
                      <option value="professional">Professional</option>
                      <option value="conversational">Conversational</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs sm:text-sm font-medium text-neutral-700 mb-2">Detail Level</label>
                    <select
                      value={settings.detailLevel}
                      onChange={(e) => handleSettingChange('detailLevel', e.target.value)}
                      className="input text-sm"
                    >
                      <option value="brief">Brief Summaries</option>
                      <option value="balanced">Balanced Detail</option>
                      <option value="comprehensive">Comprehensive Analysis</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                  <div>
                    <label className="block text-xs sm:text-sm font-medium text-neutral-700 mb-2">Response Format</label>
                    <select
                      value={settings.responseFormat}
                      onChange={(e) => handleSettingChange('responseFormat', e.target.value)}
                      className="input text-sm"
                    >
                      <option value="bullet-points">Bullet Points</option>
                      <option value="paragraphs">Paragraphs</option>
                      <option value="structured">Structured Reports</option>
                      <option value="executive">Executive Style</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs sm:text-sm font-medium text-neutral-700 mb-2">Technical Level</label>
                    <select
                      value={settings.technicalLevel}
                      onChange={(e) => handleSettingChange('technicalLevel', e.target.value)}
                      className="input text-sm"
                    >
                      <option value="simple">Simple Terms</option>
                      <option value="balanced">Balanced</option>
                      <option value="technical">Technical Jargon</option>
                      <option value="expert">Expert Level</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs sm:text-sm font-medium text-neutral-700 mb-2">Analysis Preference</label>
                  <select
                    value={settings.urgencyPreference}
                    onChange={(e) => handleSettingChange('urgencyPreference', e.target.value)}
                    className="input text-sm"
                  >
                    <option value="quick">Quick Insights</option>
                    <option value="balanced">Balanced Analysis</option>
                    <option value="thorough">Thorough Investigation</option>
                  </select>
                </div>
              </div>
            )}

            {activeTab === 'workflow' && (
              <div className="space-y-4 sm:space-y-6">
                <h3 className="text-base sm:text-lg font-semibold text-neutral-900 mb-3 sm:mb-4">Workflow Preferences</h3>

                <div>
                  <label className="block text-xs sm:text-sm font-medium text-neutral-700 mb-3">Default Content Types (Studio)</label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {['slides', 'policy-brief', 'summary', 'risk-assessment'].map((type) => (
                      <label key={type} className="flex items-center gap-2 p-3 border border-neutral-200 rounded-lg hover:bg-neutral-50">
                        <input
                          type="checkbox"
                          checked={settings.defaultContentTypes.includes(type)}
                          onChange={(e) => handleArrayChange('defaultContentTypes', type, e.target.checked)}
                          className="w-4 h-4 text-primary-600 rounded"
                        />
                        <span className="text-sm capitalize">{type.replace('-', ' ')}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs sm:text-sm font-medium text-neutral-700 mb-3">Notification Settings</label>
                  <div className="space-y-2">
                    {[
                      { id: 'content-ready', label: 'Content Generation Complete' },
                      { id: 'daily-summary', label: 'Daily Activity Summary' },
                      { id: 'security-alerts', label: 'Security & Compliance Alerts' },
                      { id: 'system-updates', label: 'System Updates' }
                    ].map((option) => (
                      <label key={option.id} className="flex items-center gap-3 p-3 border border-neutral-200 rounded-lg hover:bg-neutral-50">
                        <input
                          type="checkbox"
                          checked={settings.notificationSettings.includes(option.id)}
                          onChange={(e) => handleArrayChange('notificationSettings', option.id, e.target.checked)}
                          className="w-4 h-4 text-primary-600 rounded"
                        />
                        <span className="text-sm">{option.label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                  <div>
                    <label className="block text-xs sm:text-sm font-medium text-neutral-700 mb-2">Auto-save Duration</label>
                    <select
                      value={settings.autoSavePreference}
                      onChange={(e) => handleSettingChange('autoSavePreference', e.target.value)}
                      className="input text-sm"
                    >
                      <option value="7-days">7 Days</option>
                      <option value="30-days">30 Days</option>
                      <option value="90-days">90 Days</option>
                      <option value="1-year">1 Year</option>
                      <option value="indefinite">Indefinite</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs sm:text-sm font-medium text-neutral-700 mb-3">Export Formats</label>
                    <div className="space-y-1">
                      {['pdf', 'word', 'excel', 'powerpoint'].map((format) => (
                        <label key={format} className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={settings.exportFormats.includes(format)}
                            onChange={(e) => handleArrayChange('exportFormats', format, e.target.checked)}
                            className="w-4 h-4 text-primary-600 rounded"
                          />
                          <span className="text-sm capitalize">{format}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'department' && (
              <div className="space-y-4 sm:space-y-6">
                <h3 className="text-base sm:text-lg font-semibold text-neutral-900 mb-3 sm:mb-4">Department-Specific Settings</h3>

                <div>
                  <label className="block text-xs sm:text-sm font-medium text-neutral-700 mb-3">Focus Areas</label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {[
                      'visa-processing', 'border-security', 'customs-enforcement',
                      'identity-verification', 'risk-assessment', 'policy-development',
                      'international-relations', 'data-analysis', 'compliance-monitoring'
                    ].map((area) => (
                      <label key={area} className="flex items-center gap-2 p-3 border border-neutral-200 rounded-lg hover:bg-neutral-50">
                        <input
                          type="checkbox"
                          checked={settings.focusAreas.includes(area)}
                          onChange={(e) => handleArrayChange('focusAreas', area, e.target.checked)}
                          className="w-4 h-4 text-primary-600 rounded"
                        />
                        <span className="text-sm capitalize">{area.replace('-', ' ')}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs sm:text-sm font-medium text-neutral-700 mb-3">Typical Stakeholder Groups</label>
                  <div className="space-y-2">
                    {[
                      { id: 'ministers', label: 'Ministers & Senior Leadership' },
                      { id: 'department-heads', label: 'Department Heads' },
                      { id: 'field-teams', label: 'Field Operations Teams' },
                      { id: 'inter-agency', label: 'Inter-Agency Partners' },
                      { id: 'international', label: 'International Partners' },
                      { id: 'public', label: 'Public Communications' }
                    ].map((group) => (
                      <label key={group.id} className="flex items-center gap-3 p-3 border border-neutral-200 rounded-lg hover:bg-neutral-50">
                        <input
                          type="checkbox"
                          checked={settings.stakeholderGroups.includes(group.id)}
                          onChange={(e) => handleArrayChange('stakeholderGroups', group.id, e.target.checked)}
                          className="w-4 h-4 text-primary-600 rounded"
                        />
                        <span className="text-sm">{group.label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs sm:text-sm font-medium text-neutral-700 mb-3">Compliance Requirements</label>
                  <div className="space-y-2">
                    {[
                      { id: 'uae-federal-law', label: 'UAE Federal Law Compliance' },
                      { id: 'international-standards', label: 'International Security Standards' },
                      { id: 'gdpr', label: 'Data Protection Regulations' },
                      { id: 'anti-terrorism', label: 'Anti-Terrorism Regulations' },
                      { id: 'customs-union', label: 'GCC Customs Union Guidelines' }
                    ].map((requirement) => (
                      <label key={requirement.id} className="flex items-center gap-3 p-3 border border-neutral-200 rounded-lg hover:bg-neutral-50">
                        <input
                          type="checkbox"
                          checked={settings.complianceRequirements.includes(requirement.id)}
                          onChange={(e) => handleArrayChange('complianceRequirements', requirement.id, e.target.checked)}
                          className="w-4 h-4 text-primary-600 rounded"
                        />
                        <span className="text-sm">{requirement.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 sm:p-6 border-t border-neutral-200 bg-neutral-50 gap-3 sm:gap-0">
          <button
            onClick={resetSettings}
            className="text-neutral-600 hover:text-neutral-800 font-medium text-sm sm:text-base order-3 sm:order-1"
          >
            Reset to Defaults
          </button>
          <div className="flex items-center gap-3 order-1 sm:order-2">
            <button
              onClick={onClose}
              className="btn-secondary flex-1 sm:flex-none text-sm sm:text-base"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                saveSettings();
                onClose();
              }}
              disabled={!hasChanges}
              className="btn-primary flex items-center justify-center gap-2 disabled:opacity-50 flex-1 sm:flex-none text-sm sm:text-base"
            >
              <Save className="w-4 h-4" />
              <span className="hidden sm:inline">Save Settings</span>
              <span className="sm:hidden">Save</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}