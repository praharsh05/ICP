'use client';

import { useState, useEffect } from 'react';
import { Plus, BookOpen, Upload, MessageCircle, FileText, Search, Grid, Settings, User, Sparkles, Trash2, MoreVertical, Menu, X } from 'lucide-react';
import axios from 'axios';
import NotebookView from '../../components/NotebookView';
import SettingsModal from '../../components/SettingsModal';
import { useLanguage } from '../../contexts/LanguageContext';
import LanguageToggle from '../../components/LanguageToggle';

interface Notebook {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  document_count: number;
  chat_count: number;
}

export default function App() {
  const { t } = useLanguage();
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [selectedNotebook, setSelectedNotebook] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [newNotebookName, setNewNotebookName] = useState('');
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [deletingNotebook, setDeletingNotebook] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    // Check authentication status
    const checkAuth = () => {
      const authStatus = localStorage.getItem('isAuthenticated');
      if (authStatus === 'true') {
        setIsAuthenticated(true);
        fetchNotebooks();
      } else {
        // Redirect to landing page if not authenticated
        window.location.href = '/landing';
      }
      setCheckingAuth(false);
    };

    checkAuth();
  }, []);

  // Close mobile menu on resize to desktop
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 640) { // sm breakpoint
        setMobileMenuOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const fetchNotebooks = async () => {
    try {
      const response = await axios.get('/api/notebooks');
      setNotebooks(response.data);
    } catch (error) {
      console.error('Error fetching notebooks:', error);
    } finally {
      setLoading(false);
    }
  };

  const createNotebook = async () => {
    if (!newNotebookName.trim()) return;

    try {
      const response = await axios.post('/api/notebooks', {
        name: newNotebookName
      });
      setNotebooks([response.data, ...notebooks]);
      setNewNotebookName('');
      setIsCreating(false);
      setSelectedNotebook(response.data.id);
    } catch (error) {
      console.error('Error creating notebook:', error);
    }
  };

  const deleteNotebook = async (notebookId: string) => {
    setDeletingNotebook(notebookId);
    try {
      await axios.delete(`/api/notebooks/${notebookId}`);
      setNotebooks(notebooks.filter(nb => nb.id !== notebookId));
      setShowDeleteConfirm(null);
    } catch (error) {
      console.error('Error deleting notebook:', error);
      alert('Error deleting notebook. Please try again.');
    } finally {
      setDeletingNotebook(null);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('userEmail');
    localStorage.removeItem('userName');
    window.location.href = '/landing';
  };

  const filteredNotebooks = notebooks.filter(notebook =>
    notebook.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Show loading while checking authentication
  if (checkingAuth) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  // Only render if authenticated
  if (!isAuthenticated) {
    return null;
  }

  if (selectedNotebook) {
    return (
      <NotebookView
        notebookId={selectedNotebook}
        onBack={() => setSelectedNotebook(null)}
      />
    );
  }

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Professional ICP Header */}
      <header className="header-professional">
        <div className="content-max-width">
          <div className="flex items-center justify-between py-3 sm:py-6 px-4 sm:px-6">
            <div className="flex items-center justify-center">
              <img
                src="/icp_header.png"
                alt="ICP Header"
                className="h-12 sm:h-16 lg:h-20 w-auto max-w-none scale-x-110"
                onError={(e) => { e.currentTarget.style.display = 'none' }}
              />
            </div>

            {/* Desktop Controls */}
            <div className="hidden sm:flex items-center gap-3">
              <LanguageToggle />
              <button
                onClick={() => setShowSettings(true)}
                className="btn-ghost p-2"
                title={t('common.settings')}
              >
                <Settings className="w-5 h-5" />
              </button>
              <button
                onClick={handleLogout}
                className="btn-ghost p-2"
                title={t('common.logout')}
              >
                <User className="w-5 h-5" />
              </button>
            </div>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="sm:hidden p-2 rounded-lg hover:bg-neutral-100 transition-colors"
              title="Menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>

          {/* Mobile Menu */}
          {mobileMenuOpen && (
            <>
              {/* Overlay */}
              <div
                className="sm:hidden fixed inset-0 bg-black bg-opacity-25 z-40"
                onClick={() => setMobileMenuOpen(false)}
              />

              {/* Menu Content */}
              <div className="sm:hidden py-4 px-4 border-t border-neutral-200/60 bg-white relative z-50 shadow-lg">
                <div className="flex flex-col space-y-4">
                  <button
                    onClick={() => {
                      setShowSettings(true);
                      setMobileMenuOpen(false);
                    }}
                    className="flex items-center gap-3 py-2 text-neutral-700 hover:text-neutral-900 transition-colors"
                  >
                    <Settings className="w-5 h-5" />
                    <span className="font-medium">{t('common.settings')}</span>
                  </button>

                  <button
                    onClick={() => {
                      handleLogout();
                      setMobileMenuOpen(false);
                    }}
                    className="flex items-center gap-3 py-2 text-neutral-700 hover:text-neutral-900 transition-colors"
                  >
                    <User className="w-5 h-5" />
                    <span className="font-medium">{t('common.logout')}</span>
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </header>

      <div className="content-max-width py-4 sm:py-6 lg:py-8 px-4 sm:px-6">
        {/* Hero Section */}
        <div className="text-center mb-6 sm:mb-8 lg:mb-12 animate-fade-in px-4">
          <div className="inline-flex items-center gap-2 bg-primary-100 text-primary-800 px-3 sm:px-4 py-2 rounded-full text-xs sm:text-sm font-medium mb-4 sm:mb-6">
            <Sparkles className="w-3 h-3 sm:w-4 sm:h-4" />
            {t('hero.badge')}
          </div>
          <h2 className="text-xl sm:text-2xl lg:text-3xl xl:text-4xl font-bold text-neutral-900 mb-3 sm:mb-4 leading-tight px-2">
            {t('app.title')}
          </h2>
          <p className="text-base sm:text-lg lg:text-xl text-neutral-600 max-w-2xl mx-auto leading-relaxed px-2">
            {t('app.subtitle')}
          </p>
        </div>

        {/* Search and Create Section */}
        <div className="mb-6 sm:mb-8 animate-slide-up px-4">
          <div className="max-w-2xl mx-auto">
            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
              <div className="relative flex-1">
                <Search className="w-4 h-4 sm:w-5 sm:h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-neutral-400" />
                <input
                  type="text"
                  placeholder={t('app.search')}
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="input-search text-sm sm:text-base"
                />
              </div>
              {!isCreating ? (
                <button
                  onClick={() => setIsCreating(true)}
                  className="btn-primary flex items-center justify-center gap-2 whitespace-nowrap w-full sm:w-auto text-sm sm:text-base py-3 sm:py-2.5"
                >
                  <Plus className="w-4 h-4" />
                  {t('app.newNotebook')}
                </button>
              ) : null}
            </div>

            {isCreating && (
              <div className="mt-3 sm:mt-4 p-4 sm:p-6 card animate-slide-up">
                <h3 className="text-base sm:text-lg font-semibold text-neutral-900 mb-3 sm:mb-4">{t('app.createNotebook')}</h3>
                <div className="flex flex-col gap-3">
                  <input
                    type="text"
                    placeholder={t('app.notebookName')}
                    value={newNotebookName}
                    onChange={(e) => setNewNotebookName(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && createNotebook()}
                    className="input text-sm sm:text-base w-full"
                    autoFocus
                  />
                  <div className="flex gap-3">
                    <button onClick={createNotebook} className="btn-primary flex-1 text-sm sm:text-base py-3 sm:py-2.5">
                      {t('app.create')}
                    </button>
                    <button
                      onClick={() => {
                        setIsCreating(false);
                        setNewNotebookName('');
                      }}
                      className="btn-secondary flex-1 text-sm sm:text-base py-3 sm:py-2.5"
                    >
                      {t('app.cancel')}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Notebooks Grid */}
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : filteredNotebooks.length === 0 && searchTerm ? (
          <div className="text-center py-8 sm:py-12 px-4">
            <Search className="w-12 h-12 sm:w-16 sm:h-16 text-neutral-300 mx-auto mb-3 sm:mb-4" />
            <h3 className="text-lg sm:text-xl font-medium text-neutral-500 mb-2">{t('app.noNotebooks')}</h3>
            <p className="text-sm sm:text-base text-neutral-400">{t('app.adjustSearch')}</p>
          </div>
        ) : notebooks.length === 0 ? (
          <div className="text-center py-8 sm:py-12 px-4">
            <div className="card-accent max-w-md mx-auto">
              <BookOpen className="w-12 h-12 sm:w-16 sm:h-16 text-accent-500 mx-auto mb-3 sm:mb-4" />
              <h3 className="text-lg sm:text-xl font-semibold text-neutral-900 mb-2">{t('app.getStarted')}</h3>
              <p className="text-sm sm:text-base text-neutral-600 mb-4 sm:mb-6">{t('app.getStartedDesc')}</p>
              <button
                onClick={() => setIsCreating(true)}
                className="btn-accent flex items-center gap-2 mx-auto text-sm sm:text-base py-3 sm:py-2.5 px-4 sm:px-4"
              >
                <Plus className="w-4 h-4" />
                {t('app.createFirst')}
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4 lg:gap-6 animate-slide-up px-4">
            {filteredNotebooks.map((notebook) => (
              <div
                key={notebook.id}
                className="card-elevated hover:scale-[1.02] group relative transition-transform duration-200"
              >
                <div
                  onClick={() => setSelectedNotebook(notebook.id)}
                  className="cursor-pointer"
                >
                  <div className="flex items-start justify-between mb-3 sm:mb-4">
                    <div className="p-2 sm:p-3 bg-primary-100 rounded-xl group-hover:bg-primary-200 transition-colors">
                      <BookOpen className="w-5 h-5 sm:w-6 sm:h-6 text-primary-600" />
                    </div>
                    <div className="flex items-center gap-1 sm:gap-2">
                      <span className="text-xs text-neutral-400 font-medium hidden sm:inline">
                        {t('app.created')} {new Date(notebook.created_at).toLocaleDateString()}
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setShowDeleteConfirm(notebook.id);
                        }}
                        className="opacity-50 group-hover:opacity-100 sm:opacity-0 transition-opacity p-1 hover:bg-neutral-100 rounded"
                        title="Delete notebook"
                      >
                        <Trash2 className="w-4 h-4 text-neutral-400 hover:text-red-500" />
                      </button>
                    </div>
                  </div>

                  <h3 className="text-base sm:text-lg font-semibold text-neutral-900 mb-2 group-hover:text-primary-700 transition-colors line-clamp-2">
                    {notebook.name}
                  </h3>

                  <p className="text-xs sm:text-sm text-neutral-600 mb-3 sm:mb-4">
                    {t('app.created')} {new Date(notebook.created_at).toLocaleDateString()}
                  </p>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 sm:gap-4">
                      <span className="flex items-center gap-1 text-xs text-neutral-500">
                        <FileText className="w-3 h-3" />
                        <span className="hidden xs:inline">{notebook.document_count} {t('app.docs')}{notebook.document_count !== 1 ? 's' : ''}</span>
                        <span className="xs:hidden">{notebook.document_count}</span>
                      </span>
                      <span className="flex items-center gap-1 text-xs text-neutral-500">
                        <MessageCircle className="w-3 h-3" />
                        <span className="hidden xs:inline">{notebook.chat_count} {t('app.chats')}{notebook.chat_count !== 1 ? 's' : ''}</span>
                        <span className="xs:hidden">{notebook.chat_count}</span>
                      </span>
                    </div>
                    <div className="w-2 h-2 bg-primary-400 rounded-full"></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Features Section */}
        <div className="mt-12 sm:mt-16 lg:mt-20 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 sm:gap-6 px-4">
          <div className="card text-center group hover:scale-105 transition-transform p-4 sm:p-6">
            <div className="p-3 sm:p-4 bg-blue-100 rounded-xl w-fit mx-auto mb-4 group-hover:bg-blue-200 transition-colors">
              <Upload className="w-6 sm:w-8 h-6 sm:h-8 text-blue-600" />
            </div>
            <h3 className="font-semibold text-neutral-900 mb-2 text-sm sm:text-base">{t('feature1.title')}</h3>
            <p className="text-xs sm:text-sm text-neutral-600">{t('feature1.description')}</p>
          </div>

          <div className="card text-center group hover:scale-105 transition-transform p-4 sm:p-6">
            <div className="p-3 sm:p-4 bg-green-100 rounded-xl w-fit mx-auto mb-4 group-hover:bg-green-200 transition-colors">
              <MessageCircle className="w-6 sm:w-8 h-6 sm:h-8 text-green-600" />
            </div>
            <h3 className="font-semibold text-neutral-900 mb-2 text-sm sm:text-base">{t('feature2.title')}</h3>
            <p className="text-xs sm:text-sm text-neutral-600">{t('feature2.description')}</p>
          </div>

          <div className="card text-center group hover:scale-105 transition-transform p-4 sm:p-6">
            <div className="p-3 sm:p-4 bg-primary-100 rounded-xl w-fit mx-auto mb-4 group-hover:bg-primary-200 transition-colors">
              <Sparkles className="w-6 sm:w-8 h-6 sm:h-8 text-primary-600" />
            </div>
            <h3 className="font-semibold text-neutral-900 mb-2 text-sm sm:text-base">{t('feature3.title')}</h3>
            <p className="text-xs sm:text-sm text-neutral-600">{t('feature3.description')}</p>
          </div>

          <div className="card text-center group hover:scale-105 transition-transform p-4 sm:p-6">
            <div className="p-3 sm:p-4 bg-secondary-100 rounded-xl w-fit mx-auto mb-4 group-hover:bg-secondary-200 transition-colors">
              <BookOpen className="w-6 sm:w-8 h-6 sm:h-8 text-secondary-600" />
            </div>
            <h3 className="font-semibold text-neutral-900 mb-2 text-sm sm:text-base">{t('feature4.title')}</h3>
            <p className="text-xs sm:text-sm text-neutral-600">{t('feature4.description')}</p>
          </div>

          <div className="card text-center group hover:scale-105 transition-transform p-4 sm:p-6">
            <div className="p-3 sm:p-4 bg-accent-100 rounded-xl w-fit mx-auto mb-4 group-hover:bg-accent-200 transition-colors">
              <FileText className="w-6 sm:w-8 h-6 sm:h-8 text-accent-600" />
            </div>
            <h3 className="font-semibold text-neutral-900 mb-2 text-sm sm:text-base">{t('feature5.title')}</h3>
            <p className="text-xs sm:text-sm text-neutral-600">{t('feature5.description')}</p>
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-20 text-center py-8 border-t border-neutral-200">
          <div className="flex items-center justify-center text-neutral-600 text-sm">
            <span className="font-semibold">{t('footer.title')}</span>
          </div>
        </footer>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-4 sm:p-6">
            <div className="flex items-center gap-3 mb-3 sm:mb-4">
              <div className="p-2 bg-red-100 rounded-lg flex-shrink-0">
                <Trash2 className="w-4 h-4 sm:w-5 sm:h-5 text-red-600" />
              </div>
              <div className="min-w-0">
                <h3 className="text-base sm:text-lg font-semibold text-neutral-900">{t('app.deleteNotebook')}</h3>
                <p className="text-xs sm:text-sm text-neutral-500">{t('app.deleteConfirm')}</p>
              </div>
            </div>

            <p className="text-sm sm:text-base text-neutral-600 mb-4 sm:mb-6">
              {t('app.deleteWarning')} "<strong className="break-words">{notebooks.find(nb => nb.id === showDeleteConfirm)?.name}</strong>"?
              <span className="block mt-2">{t('app.deleteDescription')}</span>
            </p>

            <div className="flex flex-col sm:flex-row sm:justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(null)}
                className="btn-secondary text-sm sm:text-base py-3 sm:py-2.5 order-2 sm:order-1"
                disabled={deletingNotebook === showDeleteConfirm}
              >
                {t('app.cancel')}
              </button>
              <button
                onClick={() => deleteNotebook(showDeleteConfirm)}
                disabled={deletingNotebook === showDeleteConfirm}
                className="bg-red-600 hover:bg-red-700 text-white font-medium py-3 sm:py-2.5 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm sm:text-base order-1 sm:order-2"
              >
                {deletingNotebook === showDeleteConfirm ? t('app.deleting') : t('app.deleteNotebook')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Settings Modal */}
      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
      />
    </div>
  );
}