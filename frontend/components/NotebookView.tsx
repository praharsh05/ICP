'use client';

import { useState, useEffect, useRef } from 'react';
import { ArrowLeft, Upload, Send, FileText, MessageCircle, Plus, Trash2, Sparkles, Share, Settings, MoreVertical, Globe } from 'lucide-react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { useDropzone } from 'react-dropzone';
import ContentGenerator from './ContentGenerator';
import SettingsModal from './SettingsModal';
import { useLanguage } from '../contexts/LanguageContext';
import LanguageToggle from './LanguageToggle';

interface Document {
  id: string;
  original_name: string;
  summary: string;
  file_type: string;
  file_size: number;
  created_at: string;
}

interface Notebook {
  id: string;
  name: string;
  documents: Document[];
}

interface ChatMessage {
  id: string;
  message: string;
  response: string;
  sources: any[];
  created_at: string;
}

interface Props {
  notebookId: string;
  onBack: () => void;
}

export default function NotebookView({ notebookId, onBack }: Props) {
  const { t } = useLanguage();
  const [notebook, setNotebook] = useState<Notebook | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isChatting, setIsChatting] = useState(false);
  const [activePanel, setActivePanel] = useState<'sources' | 'chat' | 'studio'>('sources');
  const [activeTab, setActiveTab] = useState<'sources' | 'chat' | 'studio'>('sources');
  const [streamingResponse, setStreamingResponse] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showDropdownMenu, setShowDropdownMenu] = useState(false);
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [newNotebookName, setNewNotebookName] = useState('');
  const [showPasteTextModal, setShowPasteTextModal] = useState(false);
  const [pastedTextTitle, setPastedTextTitle] = useState('');
  const [pastedTextContent, setPastedTextContent] = useState('');
  const [showUrlModal, setShowUrlModal] = useState(false);
  const [websiteUrl, setWebsiteUrl] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchNotebook();
    fetchChatHistory();
  }, [notebookId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  const fetchNotebook = async () => {
    try {
      const response = await axios.get(`/api/notebooks/${notebookId}`);
      setNotebook(response.data);
    } catch (error) {
      console.error('Error fetching notebook:', error);
    }
  };

  const fetchChatHistory = async () => {
    try {
      const response = await axios.get(`/api/notebooks/${notebookId}/chat`);
      setChatHistory(response.data);
    } catch (error) {
      console.error('Error fetching chat history:', error);
    }
  };

  const onDrop = async (acceptedFiles: File[]) => {
    for (const file of acceptedFiles) {
      await uploadDocument(file);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md']
    },
    maxSize: 200 * 1024 * 1024 // 200MB
  });

  const uploadDocument = async (file: File) => {
    setIsUploading(true);
    const formData = new FormData();
    formData.append('document', file);

    try {
      const response = await axios.post(`/api/notebooks/${notebookId}/documents`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      fetchNotebook();
    } catch (error) {
      console.error('Error uploading document:', error);
      alert('Error uploading document. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleAddWebsite = async () => {
    if (!websiteUrl.trim()) {
      alert('Please enter a website URL');
      return;
    }

    setIsUploading(true);
    try {
      await axios.post(`/api/notebooks/${notebookId}/documents/url`, {
        url: websiteUrl
      });
      setShowUrlModal(false);
      setWebsiteUrl('');
      fetchNotebook();
    } catch (error: any) {
      console.error('Error adding website:', error);
      const errorMessage = error.response?.data?.error || 'Failed to fetch website content. Please try again.';
      alert(errorMessage);
    } finally {
      setIsUploading(false);
    }
  };

  const handlePasteText = async () => {
    if (!pastedTextTitle.trim() || !pastedTextContent.trim()) {
      alert(t('common.enterTitle') || 'Please enter both title and content');
      return;
    }

    setIsUploading(true);

    // Create a text file blob from the pasted content
    const blob = new Blob([pastedTextContent], { type: 'text/plain' });
    const file = new File([blob], `${pastedTextTitle}.txt`, { type: 'text/plain' });

    const formData = new FormData();
    formData.append('document', file);

    try {
      await axios.post(`/api/notebooks/${notebookId}/documents`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      fetchNotebook();
      setShowPasteTextModal(false);
      setPastedTextTitle('');
      setPastedTextContent('');
      alert(t('common.textAdded') || 'Text added successfully');
    } catch (error) {
      console.error('Error adding text:', error);
      alert('Error adding text. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteDocument = async (documentId: string, documentName: string) => {
    if (!confirm(t('common.deleteSourceConfirm') || `Are you sure you want to delete "${documentName}"?`)) {
      return;
    }

    try {
      await axios.delete(`/api/notebooks/${notebookId}/documents/${documentId}`);
      fetchNotebook();
      alert(t('common.sourceDeleted') || 'Source deleted successfully');
    } catch (error) {
      console.error('Error deleting document:', error);
      alert('Error deleting document. Please try again.');
    }
  };

  // Typing animation function
  const typeWriter = (text: string, callback?: () => void) => {
    setStreamingResponse('');
    setIsStreaming(true);
    let i = 0;

    const typing = () => {
      if (i < text.length) {
        setStreamingResponse(text.substring(0, i + 1));
        i++;
        setTimeout(typing, 20); // Adjust speed here (20ms = fast, 50ms = slower)
      } else {
        setIsStreaming(false);
        callback?.();
      }
    };

    typing();
  };

  const sendMessage = async () => {
    if (!currentMessage.trim() || isChatting) return;

    setIsChatting(true);
    const message = currentMessage;
    setCurrentMessage('');

    // Add user message immediately to chat history
    const tempUserMessage = {
      id: `temp-${Date.now()}`,
      message: message,
      response: '',
      sources: [],
      created_at: new Date().toISOString()
    };

    setChatHistory(prev => [...prev, tempUserMessage]);

    try {
      const response = await axios.post(`/api/notebooks/${notebookId}/chat`, {
        message: message
      });

      const botResponse = response.data.response;
      const sources = response.data.sources;

      // Start typing animation for bot response
      typeWriter(botResponse, () => {
        // Replace temp message with final message including sources
        const finalChat = {
          id: Date.now().toString(),
          message: message,
          response: botResponse,
          sources: sources,
          created_at: new Date().toISOString()
        };

        setChatHistory(prev => {
          // Remove the temp message and add final message
          const newHistory = prev.filter(chat => chat.id !== tempUserMessage.id);
          return [...newHistory, finalChat];
        });
      });

    } catch (error) {
      console.error('Error sending message:', error);
      alert('Error sending message. Please try again.');
      setCurrentMessage(message);

      // Remove the temp user message on error
      setChatHistory(prev => prev.filter(chat => chat.id !== tempUserMessage.id));
    } finally {
      setIsChatting(false);
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdownMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleRenameNotebook = async () => {
    if (!newNotebookName.trim()) return;

    try {
      await axios.put(`/api/notebooks/${notebookId}`, {
        name: newNotebookName.trim()
      });

      // Update local state
      setNotebook(prev => prev ? { ...prev, name: newNotebookName.trim() } : null);
      setShowRenameModal(false);
      setNewNotebookName('');
      setShowDropdownMenu(false);
    } catch (error) {
      console.error('Error renaming notebook:', error);
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 404) {
          alert('Notebook not found. Please refresh the page.');
        } else if (error.response?.status === 500) {
          alert('Server error. Please try again later.');
        } else {
          alert(`Error renaming notebook: ${error.response?.data?.message || error.message}`);
        }
      } else {
        alert('Error renaming notebook. Please try again.');
      }
    }
  };

  const handleDeleteNotebook = async () => {
    const confirmDelete = window.confirm(
      t('confirmDeleteNotebook') || 'Are you sure you want to delete this notebook? This action cannot be undone.'
    );

    if (confirmDelete) {
      try {
        await axios.delete(`/api/notebooks/${notebookId}`);
        onBack(); // Navigate back to notebooks list
      } catch (error) {
        console.error('Error deleting notebook:', error);
        alert('Error deleting notebook. Please try again.');
      }
    }
    setShowDropdownMenu(false);
  };

  const handleShareNotebook = () => {
    // Copy notebook URL to clipboard
    const notebookUrl = `${window.location.origin}/app?notebook=${notebookId}`;

    if (navigator.clipboard) {
      navigator.clipboard.writeText(notebookUrl).then(() => {
        alert(t('linkCopied') || 'Notebook link copied to clipboard!');
      }).catch(() => {
        // Fallback for older browsers
        fallbackCopyTextToClipboard(notebookUrl);
      });
    } else {
      // Fallback for older browsers
      fallbackCopyTextToClipboard(notebookUrl);
    }

    setShowDropdownMenu(false);
  };

  const fallbackCopyTextToClipboard = (text: string) => {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.top = '0';
    textArea.style.left = '0';
    textArea.style.position = 'fixed';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
      document.execCommand('copy');
      alert(t('linkCopied') || 'Notebook link copied to clipboard!');
    } catch (err) {
      alert('Could not copy link. Please copy manually: ' + text);
    }

    document.body.removeChild(textArea);
  };

  const formatFileSize = (bytes: number) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  if (!notebook) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-50 flex flex-col">
      {/* Professional Header */}
      <header className="header-professional">
        <div className="flex items-center justify-between py-3 px-4 sm:px-6">
          <div className="flex items-center gap-2 sm:gap-4">
            <button
              onClick={onBack}
              className="btn-ghost flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="hidden sm:inline">{t('common.back') || 'Back'}</span>
            </button>

            <img
              src="/logo.png"
              alt="Logo"
              className="h-6 sm:h-8 w-auto"
              onError={(e) => { e.currentTarget.style.display = 'none' }}
            />

            <div>
              <h1 className="text-base sm:text-lg font-semibold text-neutral-900 truncate max-w-32 sm:max-w-none">{notebook.name}</h1>
              <p className="text-xs sm:text-sm text-neutral-600">{notebook.documents.length} {t('common.sources') || 'sources'}</p>
            </div>
          </div>

          <div className="flex items-center gap-1 sm:gap-2">
            <LanguageToggle />
            <button className="btn-ghost hidden sm:flex">
              <Share className="w-4 h-4" />
            </button>
            <button
              onClick={() => setShowSettings(true)}
              className="btn-ghost hidden sm:flex"
              title={t('common.settings')}
            >
              <Settings className="w-4 h-4" />
            </button>
            <div className="relative" ref={dropdownRef}>
              <button
                className="btn-ghost"
                onClick={() => setShowDropdownMenu(!showDropdownMenu)}
                title={t('common.more') || 'More options'}
              >
                <MoreVertical className="w-4 h-4" />
              </button>

              {showDropdownMenu && (
                <div className="absolute right-0 top-full mt-2 w-48 bg-white rounded-lg shadow-lg border border-neutral-200 py-2 z-50">
                  <button
                    onClick={() => {
                      setNewNotebookName(notebook?.name || '');
                      setShowRenameModal(true);
                      setShowDropdownMenu(false);
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 flex items-center gap-2"
                  >
                    <FileText className="w-4 h-4" />
                    {t('common.rename') || 'Rename'}
                  </button>

                  <button
                    onClick={handleShareNotebook}
                    className="w-full text-left px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-50 flex items-center gap-2"
                  >
                    <Share className="w-4 h-4" />
                    {t('common.share') || 'Share'}
                  </button>

                  <hr className="my-1 border-neutral-200" />

                  <button
                    onClick={handleDeleteNotebook}
                    className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                  >
                    <Trash2 className="w-4 h-4" />
                    {t('common.delete') || 'Delete'}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Mobile Tab Navigation */}
      <div className="lg:hidden bg-white border-b border-neutral-200">
        <div className="flex overflow-x-auto scrollbar-custom">
          <button
            onClick={() => setActiveTab('sources')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
              activeTab === 'sources'
                ? 'border-primary-500 text-primary-600 bg-primary-50'
                : 'border-transparent text-neutral-600 hover:text-neutral-900'
            }`}
          >
            <FileText className="w-4 h-4" />
            {t('common.sources') || 'Sources'} ({notebook.documents.length})
          </button>
          <button
            onClick={() => setActiveTab('chat')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
              activeTab === 'chat'
                ? 'border-primary-500 text-primary-600 bg-primary-50'
                : 'border-transparent text-neutral-600 hover:text-neutral-900'
            }`}
          >
            <MessageCircle className="w-4 h-4" />
            {t('common.chat') || 'Chat'} ({chatHistory.length})
          </button>
          <button
            onClick={() => setActiveTab('studio')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
              activeTab === 'studio'
                ? 'border-primary-500 text-primary-600 bg-primary-50'
                : 'border-transparent text-neutral-600 hover:text-neutral-900'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            {t('common.studio') || 'Studio'}
          </button>
        </div>
      </div>

      {/* Three-Panel NotebookLM Layout */}
      <div className="flex-1 flex overflow-hidden p-2 gap-2">
        {/* Left Panel - Sources */}
        <div className={`w-full lg:w-[30%] bg-white rounded-lg shadow-soft flex flex-col ${
          activeTab !== 'sources' ? 'hidden lg:flex' : ''
        }`}>
          <div className="p-4 border-b border-neutral-200">
            <h2 className="text-sm font-semibold text-neutral-900 mb-3">{t('common.sources') || 'Sources'}</h2>
            <div className="grid grid-cols-3 gap-2">
              <button
                {...getRootProps()}
                className="btn-secondary text-sm flex items-center justify-center"
                disabled={isUploading}
              >
                <input {...getInputProps()} />
                <Upload className="w-4 h-4 mr-2" />
                {isUploading ? (t('common.processing') || 'Processing...') : 'Add File'}
              </button>
              <button
                onClick={() => setShowPasteTextModal(true)}
                className="btn-secondary text-sm flex items-center justify-center gap-2"
                disabled={isUploading}
              >
                <FileText className="w-4 h-4" />
                <span className="hidden sm:inline">{t('common.pasteText') || 'Paste Text'}</span>
              </button>
              <button
                onClick={() => setShowUrlModal(true)}
                className="btn-secondary text-sm flex items-center justify-center gap-2"
                disabled={isUploading}
              >
                <Globe className="w-4 h-4" />
                <span className="hidden sm:inline">Website</span>
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto scrollbar-custom">
            {notebook.documents.length === 0 ? (
              <div className="p-4 text-center text-neutral-500">
                <FileText className="w-8 h-8 mx-auto mb-2 text-neutral-300" />
                <p className="text-sm">{t('common.noSources') || 'No sources yet'}</p>
                <p className="text-xs text-neutral-400 mt-1">
                  {t('common.addFiles') || 'Add PDFs, docs, or text files'}
                </p>
              </div>
            ) : (
              <div className="p-4 space-y-3">
                {notebook.documents.map((doc) => (
                  <div key={doc.id} className="p-3 rounded-lg border border-neutral-200 hover:border-neutral-300 transition-colors group">
                    <div className="flex items-start gap-3">
                      <FileText className="w-4 h-4 text-neutral-400 mt-0.5 group-hover:text-primary-600 transition-colors flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium text-neutral-900 truncate">{doc.original_name}</h4>
                        <p className="text-xs text-neutral-500 mt-1">
                          {formatFileSize(doc.file_size)} • {doc.file_type.toUpperCase()}
                        </p>
                        <p className="text-xs text-neutral-400 mt-2 line-clamp-2">{doc.summary}</p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteDocument(doc.id, doc.original_name);
                        }}
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 hover:bg-red-50 rounded text-red-600 hover:text-red-700 flex-shrink-0"
                        title={t('common.deleteSource') || 'Delete Source'}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Center Panel - Chat */}
        <div className={`w-full lg:w-[40%] bg-white rounded-lg shadow-soft flex flex-col ${
          activeTab !== 'chat' ? 'hidden lg:flex' : ''
        }`}>
          <div className="p-4 border-b border-neutral-200">
            <h2 className="text-sm font-semibold text-neutral-900">{t('common.chat') || 'Chat'}</h2>
          </div>


          <div className="flex-1 overflow-y-auto scrollbar-custom">
            {chatHistory.length === 0 ? (
              <div className="flex items-center justify-center h-full text-center p-8">
                <div>
                  <MessageCircle className="w-12 h-12 text-neutral-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-neutral-500 mb-2">{t('common.startConversation') || 'Start a conversation'}</h3>
                  <p className="text-neutral-400 text-sm max-w-sm">
                    {notebook.documents.length === 0
                      ? (t('common.askAnything') || 'Ask anything...')
                      : (t('common.askQuestions') || 'Ask questions about your uploaded documents')}
                  </p>
                </div>
              </div>
            ) : (
              <div className="p-4 space-y-6">
                {chatHistory.map((chat) => (
                  <div key={chat.id} className="space-y-4">
                    {/* User Message */}
                    <div className="flex justify-end">
                      <div className="bg-primary-600 text-white rounded-2xl px-4 py-3 max-w-xs sm:max-w-sm text-sm">
                        {chat.message}
                      </div>
                    </div>

                    {/* AI Response - only show if there is a response */}
                    {chat.response && (
                      <div className="flex justify-start">
                        <div className="bg-white rounded-2xl border border-neutral-200 px-4 py-3 max-w-xs sm:max-w-md shadow-soft">
                          <ReactMarkdown className="prose prose-sm text-neutral-700 max-w-none text-sm">
                            {chat.response}
                          </ReactMarkdown>
                          {chat.sources && chat.sources.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-neutral-100">
                              <p className="text-xs font-medium text-neutral-600 mb-2">{t('common.sources') || 'Sources'}:</p>
                              <div className="space-y-1">
                                {chat.sources.map((source, index) => (
                                  <div key={index} className="text-xs text-neutral-500 flex items-center gap-1">
                                    <FileText className="w-3 h-3" />
                                    {source.name}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}

                {/* Streaming Response */}
                {isStreaming && (
                  <div className="flex justify-start">
                    <div className="bg-white rounded-2xl border border-neutral-200 px-4 py-3 max-w-xs sm:max-w-md shadow-soft">
                      <ReactMarkdown className="prose prose-sm text-neutral-700 max-w-none text-sm">
                        {streamingResponse}
                      </ReactMarkdown>
                      <div className="inline-block w-2 h-4 bg-primary-600 ml-1 animate-pulse"></div>
                    </div>
                  </div>
                )}

                {isChatting && !isStreaming && (
                  <div className="flex justify-start">
                    <div className="bg-white rounded-2xl border border-neutral-200 px-4 py-3 shadow-soft">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>
            )}
          </div>

          {/* Chat Input */}
          <div className="p-4 border-t border-neutral-200 bg-white">
            {/* Mode Indicator */}
            <div className="mb-3 px-2 py-1.5 bg-neutral-50 border border-neutral-200 rounded-lg">
              <p className="text-xs text-neutral-600">
                {notebook.documents.length === 0
                  ? (t('common.generalChatMode') || '💬 General chat mode - Upload documents for context-aware responses')
                  : (t('common.documentChatMode') || '📄 Document analysis mode - Responses based on your sources')}
              </p>
            </div>

            <div className="flex gap-3">
              <input
                type="text"
                value={currentMessage}
                onChange={(e) => setCurrentMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                placeholder={notebook.documents.length === 0 ? (t('common.askAnything') || 'Ask anything...') : (t('common.askAboutSources') || 'Ask about your sources...')}
                disabled={isChatting}
                className="input flex-1 text-base"
              />
              <button
                onClick={sendMessage}
                disabled={!currentMessage.trim() || isChatting}
                className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-neutral-500 mt-2 text-center sm:text-left">
              {notebook.documents.length} {t('common.source')}{notebook.documents.length !== 1 ? 's' : ''} • {chatHistory.length} {t('common.message')}{chatHistory.length !== 1 ? 's' : ''}
            </p>
          </div>
        </div>

        {/* Right Panel - Studio */}
        <div className={`w-full lg:w-[30%] bg-white rounded-lg shadow-soft flex flex-col ${
          activeTab !== 'studio' ? 'hidden lg:flex' : ''
        }`}>
          <div className="p-4 border-b border-neutral-200">
            <h2 className="text-sm font-semibold text-neutral-900 mb-1">{t('common.studio') || 'Studio'}</h2>
            <p className="text-xs text-neutral-600">{t('common.aiContentAppear') || 'AI-generated content will appear here'}</p>
          </div>

          <div className="flex-1 overflow-y-auto scrollbar-custom p-4">
            <ContentGenerator
              notebookId={notebookId}
              documentsCount={notebook.documents.length}
            />
          </div>
        </div>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
      />

      {/* Rename Modal */}
      {showRenameModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-semibold text-neutral-900 mb-4">
              {t('common.renameNotebook') || 'Rename Notebook'}
            </h3>

            <input
              type="text"
              value={newNotebookName}
              onChange={(e) => setNewNotebookName(e.target.value)}
              className="input mb-4"
              placeholder={t('common.notebookName') || 'Notebook name'}
              autoFocus
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleRenameNotebook();
                }
              }}
            />

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowRenameModal(false);
                  setNewNotebookName('');
                }}
                className="btn-secondary"
              >
                {t('common.cancel') || 'Cancel'}
              </button>
              <button
                onClick={handleRenameNotebook}
                className="btn-primary"
                disabled={!newNotebookName.trim()}
              >
                {t('common.save') || 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Paste Text Modal */}
      {showPasteTextModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-neutral-200">
              <h3 className="text-lg font-semibold text-neutral-900">
                {t('common.pasteTextSource') || 'Paste Text as Source'}
              </h3>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  {t('common.textTitle') || 'Text Title'}
                </label>
                <input
                  type="text"
                  value={pastedTextTitle}
                  onChange={(e) => setPastedTextTitle(e.target.value)}
                  placeholder={t('common.enterTitle') || 'Enter text title...'}
                  className="input"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  {t('common.content') || 'Content'}
                </label>
                <textarea
                  value={pastedTextContent}
                  onChange={(e) => setPastedTextContent(e.target.value)}
                  placeholder={t('common.pasteContent') || 'Paste your content here...'}
                  className="input min-h-[300px] resize-y"
                  rows={12}
                />
              </div>
            </div>

            <div className="p-6 border-t border-neutral-200 flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowPasteTextModal(false);
                  setPastedTextTitle('');
                  setPastedTextContent('');
                }}
                className="btn-secondary"
              >
                {t('common.cancel') || 'Cancel'}
              </button>
              <button
                onClick={handlePasteText}
                className="btn-primary"
                disabled={!pastedTextTitle.trim() || !pastedTextContent.trim() || isUploading}
              >
                {isUploading ? (t('common.processing') || 'Processing...') : (t('common.addAsSource') || 'Add as Source')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Website Modal */}
      {showUrlModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="p-6 border-b border-neutral-200">
              <h3 className="text-lg font-semibold text-neutral-900 flex items-center gap-2">
                <Globe className="w-5 h-5 text-blue-600" />
                Add Website
              </h3>
            </div>

            <div className="p-6">
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                Website URL
              </label>
              <input
                type="url"
                value={websiteUrl}
                onChange={(e) => setWebsiteUrl(e.target.value)}
                placeholder="https://example.com"
                className="input"
                autoFocus
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && websiteUrl.trim()) {
                    handleAddWebsite();
                  }
                }}
              />
              <p className="text-xs text-neutral-500 mt-2">
                Enter a website URL to extract its content and add it as a source document.
              </p>
            </div>

            <div className="p-6 border-t border-neutral-200 flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowUrlModal(false);
                  setWebsiteUrl('');
                }}
                className="btn-secondary"
                disabled={isUploading}
              >
                Cancel
              </button>
              <button
                onClick={handleAddWebsite}
                className="btn-primary"
                disabled={!websiteUrl.trim() || isUploading}
              >
                {isUploading ? 'Fetching...' : 'Add Website'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}