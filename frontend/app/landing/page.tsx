'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight, Brain, BookText, ShieldCheck, Globe, Lightbulb, Settings, Shield, Zap, Users, CheckCircle, Menu, X, FileText, Sparkles } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';
import LanguageToggle from '../../components/LanguageToggle';

export default function LandingPage() {
  const { t, language } = useLanguage();
  const router = useRouter();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState<'citizens' | 'residents' | null>(null);
  const [unifiedId, setUnifiedId] = useState('');

  const handleGenerateTree = () => {
    if (!selectedProfile || !unifiedId.trim()) return;

    // Store profile selection
    localStorage.setItem('profileType', selectedProfile);

    // Navigate to tree visualization page
    router.push(`/tree/${unifiedId}?type=${selectedProfile}`);
  };



  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 sm:h-20 lg:h-24">
            <div className="flex items-center justify-center">
              <img
                src="/icp_header.png"
                alt="ICP Header"
                className="h-12 sm:h-16 lg:h-20 w-auto max-w-none scale-x-110"
                onError={(e) => { e.currentTarget.style.display = 'none' }}
              />
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-neutral-600 hover:text-neutral-900 transition-colors">{t('header.features')}</a>
              <a href="#about" className="text-neutral-600 hover:text-neutral-900 transition-colors">{t('header.about')}</a>
              <LanguageToggle />
              <button
                onClick={() => {
                  setShowAuthModal(true);
                }}
                className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg transition-colors"
              >
                {t('header.accessSystem')}
              </button>
            </nav>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg hover:bg-neutral-100"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>

          {/* Mobile Menu */}
          {mobileMenuOpen && (
            <div className="md:hidden py-4 border-t border-neutral-200">
              <nav className="flex flex-col space-y-4">
                <a href="#features" className="text-neutral-600 hover:text-neutral-900">{t('header.features')}</a>
                <a href="#about" className="text-neutral-600 hover:text-neutral-900">{t('header.about')}</a>
                <LanguageToggle />
                <button
                  onClick={() => {
                    setShowAuthModal(true);
                    setMobileMenuOpen(false);
                  }}
                  className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-center"
                >
                  {t('header.accessSystem')}
                </button>
              </nav>
            </div>
          )}
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden hero-gradient">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16 lg:py-32">
          <div className="lg:grid lg:grid-cols-12 lg:gap-8 items-center">
            <div className="lg:col-span-6 animate-fade-in-up text-center lg:text-left">
              <div className="inline-flex items-center gap-2 bg-primary-100 text-primary-800 px-4 py-2 rounded-full text-sm font-medium mb-6 animate-scale-in">
                <Sparkles className="w-4 h-4" />
                {t('hero.badge')}
              </div>

              <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-neutral-900 mb-6 leading-tight">
                <span className="text-primary-600 block bg-gradient-to-r from-primary-600 to-primary-700 bg-clip-text text-transparent">{t('hero.title')}</span>
              </h1>

              <p className="text-lg sm:text-xl text-neutral-600 mb-8 max-w-2xl leading-relaxed mx-auto lg:mx-0">
                {t('hero.subtitle')}
              </p>

              <div className="flex flex-col sm:flex-row gap-4 mb-12 max-w-md mx-auto lg:mx-0 lg:max-w-none">
                <button
                  onClick={() => {
                    setShowAuthModal(true);
                  }}
                  className="bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 text-white px-8 py-4 rounded-lg font-semibold flex items-center justify-center gap-2 transition-all duration-300 shadow-medium hover:shadow-strong hover:-translate-y-0.5"
                >
                  {t('hero.accessSystem')}
                  <ArrowRight className="w-5 h-5" />
                </button>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-6 text-sm text-neutral-500 justify-center lg:justify-start">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-green-500" />
                  {t('hero.secure')}
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-green-500" />
                  {t('hero.governmentGrade')}
                </div>
              </div>
            </div>

            <div className="lg:col-span-6 mt-8 sm:mt-12 lg:mt-0 animate-fade-in-up px-4 sm:px-0" style={{ animationDelay: '0.2s' }}>
              <div className="relative">
                <div className="glass-card rounded-2xl shadow-2xl p-6 border border-neutral-200/50">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-3 h-3 bg-red-400 rounded-full"></div>
                    <div className="w-3 h-3 bg-yellow-400 rounded-full"></div>
                    <div className="w-3 h-3 bg-green-400 rounded-full"></div>
                  </div>

                  <div className="space-y-4">
                    <div className="flex items-center gap-3 p-3 bg-neutral-50/80 rounded-lg">
                      <Users className="w-5 h-5 text-primary-600" />
                      <div>
                        <div className="font-medium text-sm">Family Relationship Intelligence</div>
                        <div className="text-xs text-neutral-500">Evidence-based connections</div>
                      </div>
                    </div>

                    <div className="bg-gradient-to-r from-primary-50 to-primary-100 p-4 rounded-lg">
                      <div className="text-sm font-medium text-neutral-900 mb-3">Family Tree View:</div>
                      <div className="flex items-center justify-center gap-4 mb-3">
                        <div className="flex flex-col items-center">
                          <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                            P1
                          </div>
                          <div className="text-xs mt-1 text-neutral-700">Hassan</div>
                        </div>
                        <div className="flex flex-col gap-2">
                          <div className="w-8 h-0.5 bg-neutral-400"></div>
                          <div className="w-8 h-0.5 bg-neutral-400"></div>
                        </div>
                        <div className="flex flex-col gap-2">
                          <div className="flex flex-col items-center">
                            <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                              P2
                            </div>
                            <div className="text-xs mt-1 text-neutral-700">Ali</div>
                          </div>
                          <div className="flex flex-col items-center">
                            <div className="w-8 h-8 bg-purple-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                              P3
                            </div>
                            <div className="text-xs mt-1 text-neutral-700">Fatima</div>
                          </div>
                        </div>
                      </div>
                      <div className="text-xs text-neutral-600 text-center">
                        3 generations • 12 verified connections
                      </div>
                    </div>

                    <div className="flex gap-2">
                      <button className="flex-1 bg-primary-600 hover:bg-primary-700 text-white text-xs py-2 px-3 rounded-lg transition-colors">
                        Explore Tree
                      </button>
                      <button className="flex-1 border border-neutral-200 hover:border-neutral-300 text-neutral-700 text-xs py-2 px-3 rounded-lg transition-colors">
                        Find LCA
                      </button>
                    </div>
                  </div>
                </div>

                {/* Floating Elements */}
                <div className="absolute -top-4 -right-4 bg-green-500 text-white p-3 rounded-xl shadow-lg floating-element">
                  <Users className="w-5 h-5" />
                </div>
                <div className="absolute -bottom-4 -left-4 bg-blue-500 text-white p-3 rounded-xl shadow-lg floating-element-delayed">
                  <Shield className="w-5 h-5" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-20 animate-fade-in-up">
            <h2 className="text-3xl md:text-4xl font-bold text-neutral-900 mb-4">
              {t('features.title')}
            </h2>
            <p className="text-xl text-neutral-600 max-w-3xl mx-auto">
              {t('features.subtitle')}
            </p>
          </div>

          {/* Feature 1: Work Smarter with Your Documents */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center mb-20">
            <div className="animate-fade-in-up">
              <h3 className="text-2xl md:text-3xl font-bold text-neutral-900 mb-4">
                {t('feature1.title')}
              </h3>
              <p className="text-lg text-neutral-600 mb-6 leading-relaxed">
                {t('feature1.description')}
              </p>
              <div className="flex items-center gap-4">
                <div className="bg-blue-100 p-3 rounded-lg">
                  <Brain className="w-6 h-6 text-blue-600" />
                </div>
                <span className="text-neutral-700 font-medium">{t('feature1.badge')}</span>
              </div>
            </div>
            <div className="animate-fade-in-up lg:pl-8 mt-8 lg:mt-0" style={{ animationDelay: '0.2s' }}>
              <div className="bg-gradient-to-br from-blue-50 to-primary-50 rounded-2xl p-6 sm:p-8 shadow-lg">
                <div className="bg-white rounded-lg p-4 sm:p-6 mb-4 shadow-sm">
                  <div className="flex items-center gap-3 mb-3">
                    <Users className="w-5 h-5 text-blue-600" />
                    <span className="font-semibold text-sm">ID → Tree Generation</span>
                  </div>
                  <div className="flex items-center justify-center my-4">
                    <div className="text-center">
                      <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center text-white font-bold mb-2 mx-auto">
                        ID
                      </div>
                      <div className="text-xs text-blue-600">→</div>
                      <div className="flex gap-2 mt-2 justify-center">
                        <div className="w-8 h-8 bg-green-400 rounded-full"></div>
                        <div className="w-8 h-8 bg-purple-400 rounded-full"></div>
                        <div className="w-8 h-8 bg-orange-400 rounded-full"></div>
                      </div>
                    </div>
                  </div>
                  <p className="text-xs text-neutral-600 text-center">Instant tree generation • Sub-second</p>
                </div>
                <div className="text-center">
                  <ShieldCheck className="w-12 h-12 text-primary-600 mx-auto" />
                  <p className="text-sm text-neutral-600 mt-2">Evidence-based relationships</p>
                </div>
              </div>
            </div>
          </div>

          {/* Feature 2: AI Document Assistant for Government Teams */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center mb-12 sm:mb-16 lg:mb-20">
            <div className="animate-fade-in-up lg:pr-8 lg:order-2">
              <h3 className="text-xl sm:text-2xl lg:text-3xl font-bold text-neutral-900 mb-4">
                {t('feature2.title')}
              </h3>
              <p className="text-base sm:text-lg text-neutral-600 mb-6 leading-relaxed">
                {t('feature2.description')}
              </p>
              <div className="flex items-center gap-4">
                <div className="bg-green-100 p-3 rounded-lg">
                  <BookText className="w-6 h-6 text-green-600" />
                </div>
                <span className="text-neutral-700 font-medium">{t('feature2.badge')}</span>
              </div>
            </div>
            <div className="animate-fade-in-up lg:order-1" style={{ animationDelay: '0.2s' }}>
              <div className="bg-gradient-to-br from-green-50 to-accent-50 rounded-2xl p-8 shadow-lg">
                <div className="bg-white rounded-lg p-4 mb-4 shadow-sm">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-semibold text-neutral-900">Family Book Structure</span>
                    <BookText className="w-4 h-4 text-green-600" />
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-xs">
                      <div className="w-6 h-6 bg-blue-500 rounded-full"></div>
                      <span className="text-neutral-700">Head of Family</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs pl-4">
                      <div className="w-5 h-5 bg-pink-400 rounded-full"></div>
                      <span className="text-neutral-600">Spouse(s)</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs pl-8">
                      <div className="w-4 h-4 bg-green-400 rounded-full"></div>
                      <span className="text-neutral-600">Children</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Users className="w-8 h-8 text-green-600" />
                  <span className="text-sm text-neutral-700">Official family-book rules applied</span>
                </div>
              </div>
            </div>
          </div>

          {/* Feature 3: SmartDocs: Your Productivity Partner */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center mb-12 sm:mb-16 lg:mb-20">
            <div className="animate-fade-in-up">
              <h3 className="text-xl sm:text-2xl lg:text-3xl font-bold text-neutral-900 mb-4">
                {t('feature3.title')}
              </h3>
              <p className="text-base sm:text-lg text-neutral-600 mb-6 leading-relaxed">
                {t('feature3.description')}
              </p>
              <div className="flex items-center gap-4">
                <div className="bg-primary-100 p-3 rounded-lg">
                  <ShieldCheck className="w-6 h-6 text-primary-600" />
                </div>
                <span className="text-neutral-700 font-medium">{t('feature3.badge')}</span>
              </div>
            </div>
            <div className="animate-fade-in-up lg:pl-8" style={{ animationDelay: '0.2s' }}>
              <div className="bg-gradient-to-br from-primary-50 to-blue-50 rounded-2xl p-8 shadow-lg">
                <div className="bg-white rounded-lg p-6 shadow-sm">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-semibold text-neutral-900">Resident Network</span>
                    <Globe className="w-5 h-5 text-primary-600" />
                  </div>
                  <div className="flex items-center justify-center gap-6 mb-4">
                    <div className="text-center">
                      <div className="w-12 h-12 bg-orange-500 rounded-full flex items-center justify-center text-white text-xs font-bold mb-1">
                        SP
                      </div>
                      <div className="text-xs text-neutral-600">Sponsor</div>
                    </div>
                    <div className="flex flex-col gap-1">
                      <div className="w-12 h-0.5 bg-orange-300"></div>
                      <div className="w-12 h-0.5 bg-orange-300"></div>
                      <div className="w-12 h-0.5 bg-orange-300"></div>
                    </div>
                    <div className="flex flex-col gap-3">
                      <div className="text-center">
                        <div className="w-8 h-8 bg-teal-400 rounded-full flex items-center justify-center text-white text-xs">
                          D1
                        </div>
                        <div className="text-xs text-neutral-600">Dep</div>
                      </div>
                      <div className="text-center">
                        <div className="w-8 h-8 bg-teal-400 rounded-full flex items-center justify-center text-white text-xs">
                          D2
                        </div>
                        <div className="text-xs text-neutral-600">Dep</div>
                      </div>
                    </div>
                  </div>
                  <div className="text-xs text-neutral-600 text-center pt-3 border-t border-neutral-200">
                    Evidence-based • Time-aware mapping
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Feature 4: Documents Made Simple with AI */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center mb-12 sm:mb-16 lg:mb-20">
            <div className="animate-fade-in-up lg:pr-8 lg:order-2">
              <h3 className="text-xl sm:text-2xl lg:text-3xl font-bold text-neutral-900 mb-4">
                {t('feature4.title')}
              </h3>
              <p className="text-base sm:text-lg text-neutral-600 mb-6 leading-relaxed">
                {t('feature4.description')}
              </p>
              <div className="flex items-center gap-4">
                <div className="bg-secondary-100 p-3 rounded-lg">
                  <Globe className="w-6 h-6 text-secondary-600" />
                </div>
                <span className="text-neutral-700 font-medium">{t('feature4.badge')}</span>
              </div>
            </div>
            <div className="animate-fade-in-up lg:order-1" style={{ animationDelay: '0.2s' }}>
              <div className="bg-gradient-to-br from-secondary-50 to-neutral-50 rounded-2xl p-8 shadow-lg">
                <div className="bg-white rounded-lg p-6 shadow-sm">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-semibold text-neutral-900">Common Ancestor (LCA)</span>
                    <div className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded font-medium">Found</div>
                  </div>
                  <div className="flex flex-col items-center gap-4 mb-4">
                    {/* Common Ancestor at top */}
                    <div className="text-center">
                      <div className="w-14 h-14 bg-amber-500 rounded-full flex items-center justify-center text-white text-sm font-bold mb-1 shadow-md">
                        CA
                      </div>
                      <div className="text-xs text-neutral-700 font-semibold">Ahmad (Common)</div>
                    </div>
                    {/* Connection lines */}
                    <div className="flex items-start gap-16">
                      <div className="flex flex-col items-center">
                        <div className="w-0.5 h-8 bg-purple-300"></div>
                        <div className="w-12 h-12 bg-purple-500 rounded-full flex items-center justify-center text-white text-xs font-bold mb-1">
                          P1
                        </div>
                        <div className="text-xs text-neutral-600">Sara</div>
                      </div>
                      <div className="flex flex-col items-center">
                        <div className="w-0.5 h-8 bg-indigo-300"></div>
                        <div className="w-12 h-12 bg-indigo-500 rounded-full flex items-center justify-center text-white text-xs font-bold mb-1">
                          P2
                        </div>
                        <div className="text-xs text-neutral-600">Khalid</div>
                      </div>
                    </div>
                  </div>
                  <div className="text-xs text-neutral-600 text-center pt-3 border-t border-neutral-200">
                    Graph-based LCA • Multi-path detection
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Feature 5: From Files to Fast Insights */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center mb-12 sm:mb-16 lg:mb-20">
            <div className="animate-fade-in-up">
              <h3 className="text-xl sm:text-2xl lg:text-3xl font-bold text-neutral-900 mb-4">
                {t('feature5.title')}
              </h3>
              <p className="text-base sm:text-lg text-neutral-600 mb-6 leading-relaxed">
                {t('feature5.description')}
              </p>
              <div className="flex items-center gap-4">
                <div className="bg-accent-100 p-3 rounded-lg">
                  <Lightbulb className="w-6 h-6 text-accent-600" />
                </div>
                <span className="text-neutral-700 font-medium">{t('feature5.badge')}</span>
              </div>
            </div>
            <div className="animate-fade-in-up lg:pl-8" style={{ animationDelay: '0.2s' }}>
              <div className="bg-gradient-to-br from-accent-50 to-primary-50 rounded-2xl p-8 shadow-lg">
                <div className="bg-white rounded-lg p-4 shadow-sm mb-4">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-sm font-semibold">Query Performance</span>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="text-neutral-600">Tree Depth Explored</span>
                      <span className="text-accent-600 font-medium">4 generations</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-neutral-600">Nodes Traversed</span>
                      <span className="text-blue-600 font-medium">142 persons</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-neutral-600">Response Time</span>
                      <span className="text-green-600 font-bold">0.18s</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-neutral-600">Cache Hit Rate</span>
                      <span className="text-purple-600 font-medium">94%</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-center">
                  <Zap className="w-8 h-8 text-accent-500" />
                </div>
              </div>
            </div>
          </div>

          {/* Feature 6: Arabic Language Support */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
            <div className="animate-fade-in-up lg:pr-8 lg:order-2">
              <h3 className="text-xl sm:text-2xl lg:text-3xl font-bold text-neutral-900 mb-4">
                {t('feature6.title')}
                <span className="block text-lg mt-2" dir="rtl">دعم اللغة العربية</span>
              </h3>
              <p className="text-base sm:text-lg text-neutral-600 mb-6 leading-relaxed">
                {t('feature6.description')}
              </p>
              <div className="flex items-center gap-4">
                <div className="bg-orange-100 p-3 rounded-lg">
                  <Settings className="w-6 h-6 text-orange-600" />
                </div>
                <span className="text-neutral-700 font-medium">{t('feature6.badge')}</span>
              </div>
            </div>
            <div className="animate-fade-in-up lg:order-1" style={{ animationDelay: '0.2s' }}>
              <div className="bg-gradient-to-br from-orange-50 to-amber-50 rounded-2xl p-8 shadow-lg">
                <div className="relative">
                  {/* Simple graph node that "has been hovered" */}
                  <div className="flex items-center justify-center mb-4">
                    <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center text-white text-xs font-bold cursor-pointer shadow-md">
                      M
                    </div>
                  </div>
                  {/* Hover Card Info Panel */}
                  <div className="bg-white rounded-lg p-4 shadow-xl border-2 border-orange-300">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-bold text-neutral-900">Mohammed Ali Hassan</span>
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    </div>
                    <div className="space-y-2 text-xs">
                      <div className="flex justify-between">
                        <span className="text-neutral-600">ID:</span>
                        <span className="text-neutral-800 font-medium">P1292597966</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-neutral-600">Birth Date:</span>
                        <span className="text-neutral-800 font-medium">1982-04-15</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-neutral-600">Relation:</span>
                        <span className="text-blue-600 font-medium">Father</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-neutral-600">Status:</span>
                        <span className="text-green-600 font-medium">Active</span>
                      </div>
                    </div>
                    <div className="mt-3 pt-3 border-t border-neutral-200 text-xs text-neutral-600">
                      Hover to view • Click to explore tree
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Feature 7: Clarity from Complexity */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center mb-12 sm:mb-16 lg:mb-20">
            <div className="animate-fade-in-up">
              <h3 className="text-xl sm:text-2xl lg:text-3xl font-bold text-neutral-900 mb-4">
                {t('feature7.title')}
              </h3>
              <p className="text-base sm:text-lg text-neutral-600 mb-6 leading-relaxed">
                {t('feature7.description')}
              </p>
              <div className="flex items-center gap-4">
                <div className="bg-purple-100 p-3 rounded-lg">
                  <FileText className="w-6 h-6 text-purple-600" />
                </div>
                <span className="text-neutral-700 font-medium">{t('feature7.badge')}</span>
              </div>
            </div>
            <div className="animate-fade-in-up lg:pl-8" style={{ animationDelay: '0.2s' }}>
              <div className="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-2xl p-8 shadow-lg">
                <div className="bg-white rounded-lg p-4 shadow-sm mb-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-semibold text-neutral-900">Scalability Roadmap</span>
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-green-500 rounded flex items-center justify-center text-white text-xs font-bold">
                        ✓
                      </div>
                      <div className="text-xs">
                        <div className="font-semibold text-neutral-900">PoC Phase</div>
                        <div className="text-neutral-600">100K records • 3 data sources</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-blue-500 rounded flex items-center justify-center text-white text-xs font-bold">
                        →
                      </div>
                      <div className="text-xs">
                        <div className="font-semibold text-neutral-900">Pilot Phase</div>
                        <div className="text-neutral-600">5M records • 10+ sources</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-purple-400 rounded flex items-center justify-center text-white text-xs font-bold">
                        ⚡
                      </div>
                      <div className="text-xs">
                        <div className="font-semibold text-neutral-900">Production Ready</div>
                        <div className="text-neutral-600">50M+ records • Real-time sync</div>
                      </div>
                    </div>
                  </div>
                  <div className="mt-3 pt-3 border-t border-neutral-200 text-xs text-neutral-600 text-center">
                    Architecture proven • Cloud-native design
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Feature 8: Government-Grade Intelligence */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
            <div className="animate-fade-in-up lg:pr-8 lg:order-2">
              <h3 className="text-xl sm:text-2xl lg:text-3xl font-bold text-neutral-900 mb-4">
                {t('feature8.title')}
              </h3>
              <p className="text-base sm:text-lg text-neutral-600 mb-6 leading-relaxed">
                {t('feature8.description')}
              </p>
              <div className="flex items-center gap-4">
                <div className="bg-emerald-100 p-3 rounded-lg">
                  <Shield className="w-6 h-6 text-emerald-600" />
                </div>
                <span className="text-neutral-700 font-medium">{t('feature8.badge')}</span>
              </div>
            </div>
            <div className="animate-fade-in-up lg:order-1" style={{ animationDelay: '0.2s' }}>
              <div className="bg-gradient-to-br from-emerald-50 to-green-50 rounded-2xl p-8 shadow-lg">
                <div className="bg-white rounded-lg p-6 shadow-sm">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-semibold text-neutral-900">Security & Deployment</span>
                    <Shield className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div className="space-y-3 mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-emerald-500 rounded-full flex items-center justify-center text-white text-xs">
                        🔒
                      </div>
                      <div className="text-xs">
                        <div className="font-semibold text-neutral-900">On-Premise Only</div>
                        <div className="text-neutral-600">100% data sovereignty</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-xs">
                        🛡️
                      </div>
                      <div className="text-xs">
                        <div className="font-semibold text-neutral-900">Air-Gapped Design</div>
                        <div className="text-neutral-600">No external dependencies</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-purple-500 rounded-full flex items-center justify-center text-white text-xs">
                        ✓
                      </div>
                      <div className="text-xs">
                        <div className="font-semibold text-neutral-900">Audit Ready</div>
                        <div className="text-neutral-600">Full compliance framework</div>
                      </div>
                    </div>
                  </div>
                  <div className="text-xs text-emerald-700 bg-emerald-50 p-2 rounded text-center">
                    Sensitive data stays in your infrastructure
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>


      {/* CTA Section */}
      <section className="py-12 sm:py-16 lg:py-20 cta-gradient animate-gradient">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8 animate-fade-in-up">
          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-white mb-6">
            {t('cta.title')}
          </h2>
          <p className="text-lg sm:text-xl text-blue-100 mb-8">
            {t('cta.subtitle')}
          </p>
          <button
            onClick={() => {
              setAuthMode('signup');
              setShowAuthModal(true);
            }}
            className="bg-white text-primary-600 hover:bg-neutral-50 px-8 py-4 rounded-lg font-semibold text-lg transition-all duration-300 inline-flex items-center gap-2 shadow-medium hover:shadow-strong hover:-translate-y-0.5"
          >
            {t('cta.button')}
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-neutral-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="mb-4">
              <h3 className="text-lg font-bold text-white">{t('footer.title')}</h3>
            </div>
            <p className="text-neutral-400 text-sm">
              {t('footer.authority')}
            </p>
          </div>

          <div className="border-t border-neutral-800 mt-8 pt-8 text-center text-sm text-neutral-400">
            <p>&copy; 2025 {t('footer.title')}</p>
          </div>
        </div>
      </footer>

      {/* Profile Type Modal */}
      {showAuthModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full mx-4 p-6 sm:p-8 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-2xl font-bold text-neutral-900 mb-2">
                  {t('profile.title')}
                </h2>
                <p className="text-sm text-neutral-600">
                  {t('profile.subtitle')}
                </p>
              </div>
              <button
                onClick={() => setShowAuthModal(false)}
                className="text-neutral-500 hover:text-neutral-700"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              {/* Citizens Option */}
              <button
                onClick={() => setSelectedProfile('citizens')}
                className={`p-6 rounded-xl border-2 transition-all text-left ${
                  selectedProfile === 'citizens'
                    ? 'border-primary-600 bg-primary-50'
                    : 'border-neutral-200 hover:border-primary-300 hover:bg-neutral-50'
                }`}
              >
                <div className="flex items-center gap-3 mb-3">
                  <Users className="w-6 h-6 text-primary-600" />
                  <h3 className="text-lg font-semibold text-neutral-900">
                    {t('profile.citizens')}
                  </h3>
                </div>
                <p className="text-sm text-neutral-600">
                  {t('profile.citizensDesc')}
                </p>
              </button>

              {/* Residents Option */}
              <button
                onClick={() => setSelectedProfile('residents')}
                className={`p-6 rounded-xl border-2 transition-all text-left ${
                  selectedProfile === 'residents'
                    ? 'border-primary-600 bg-primary-50'
                    : 'border-neutral-200 hover:border-primary-300 hover:bg-neutral-50'
                }`}
              >
                <div className="flex items-center gap-3 mb-3">
                  <Globe className="w-6 h-6 text-primary-600" />
                  <h3 className="text-lg font-semibold text-neutral-900">
                    {t('profile.residents')}
                  </h3>
                </div>
                <p className="text-sm text-neutral-600">
                  {t('profile.residentsDesc')}
                </p>
              </button>
            </div>

            {/* Unified ID Input */}
            {selectedProfile && (
              <div className="mb-6">
                <label htmlFor="unifiedId" className="block text-sm font-medium text-neutral-700 mb-2">
                  Unified ID
                </label>
                <input
                  type="text"
                  id="unifiedId"
                  value={unifiedId}
                  onChange={(e) => setUnifiedId(e.target.value)}
                  placeholder="Enter Unified ID (e.g., P1968702237)"
                  className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleGenerateTree();
                    }
                  }}
                />
              </div>
            )}

            <button
              onClick={handleGenerateTree}
              disabled={!selectedProfile || !unifiedId.trim()}
              className="w-full bg-primary-600 hover:bg-primary-700 disabled:bg-neutral-300 disabled:cursor-not-allowed text-white py-3 px-4 rounded-lg font-semibold transition-colors"
            >
              Generate Family Tree
            </button>

            <p className="text-xs text-neutral-500 text-center mt-4">
              {t('profile.evidenceBased')}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}