'use client';

import { useState } from 'react';
import { Presentation, GraduationCap, FileText, Lightbulb, Download, Loader2, Podcast } from 'lucide-react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

interface Props {
  notebookId: string;
  documentsCount: number;
}

interface GeneratedContent {
  type: string;
  content: string;
  generatedAt: string;
  documentCount: number;
}

export default function ContentGenerator({ notebookId, documentsCount }: Props) {
  const [generatedContent, setGeneratedContent] = useState<GeneratedContent | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeType, setActiveType] = useState<string>('');
  const [showLanguageSelect, setShowLanguageSelect] = useState(false);

  const contentTypes = [
    {
      id: 'slides',
      title: 'Generate Slides',
      description: 'Create presentation slides from your documents',
      icon: Presentation,
      color: 'bg-white hover:bg-blue-50 border-2 border-blue-500 hover:border-blue-600 !text-blue-600 hover:!text-blue-700 font-medium',
    },
    {
      id: 'policy-brief',
      title: 'Policy Brief',
      description: 'Generate policy recommendations and briefings',
      icon: FileText,
      color: 'bg-white hover:bg-blue-50 border-2 border-blue-500 hover:border-blue-600 !text-blue-600 hover:!text-blue-700 font-medium',
    },
    {
      id: 'summary',
      title: 'Executive Summary',
      description: 'Create comprehensive document summaries',
      icon: FileText,
      color: 'bg-white hover:bg-blue-50 border-2 border-blue-500 hover:border-blue-600 !text-blue-600 hover:!text-blue-700 font-medium',
    },
    {
      id: 'risk-assessment',
      title: 'Risk Assessment',
      description: 'Identify potential risks and mitigation strategies',
      icon: Lightbulb,
      color: 'bg-white hover:bg-blue-50 border-2 border-blue-500 hover:border-blue-600 !text-blue-600 hover:!text-blue-700 font-medium',
    },
    {
      id: 'audio-overview',
      title: 'Audio Podcast',
      description: 'Generate AI podcast from your documents',
      icon: Podcast,
      color: 'bg-white hover:bg-blue-50 border-2 border-blue-500 hover:border-blue-600 !text-blue-600 hover:!text-blue-700 font-medium',
    },
    {
      id: 'smartbook',
      title: 'SmartBook',
      description: 'Educational audiobook for young learners',
      icon: Podcast,
      color: 'bg-white hover:bg-blue-50 border-2 border-blue-500 hover:border-blue-600 !text-blue-600 hover:!text-blue-700 font-medium',
    },
  ];

  const generateContent = async (type: string, language?: string) => {
    if (documentsCount === 0) {
      alert('Please upload documents first before generating content.');
      return;
    }

    // Show language selection modal for podcast and smartbook
    if ((type === 'audio-overview' || type === 'smartbook') && !language) {
      setActiveType(type);
      setShowLanguageSelect(true);
      return;
    }

    setIsGenerating(true);
    setActiveType(type);
    setShowLanguageSelect(false);

    try {
      const response = await axios.post(`/api/notebooks/${notebookId}/generate/${type}`, {
        language: language
      });

      // Handle async podcast/smartbook generation
      if ((type === 'audio-overview' || type === 'smartbook') && response.data.jobId) {
        const jobId = response.data.jobId;

        // Poll for job completion
        const pollInterval = setInterval(async () => {
          try {
            const statusResponse = await axios.get(`/api/podcasts/${jobId}/status`);
            const job = statusResponse.data;

            if (job.status === 'completed') {
              clearInterval(pollInterval);
              setGeneratedContent({
                type: type,
                content: job.audioPath,
                generatedAt: job.completedAt,
                documentCount: response.data.documentCount,
                script: job.script
              } as any);
              setIsGenerating(false);
              setActiveType('');
            } else if (job.status === 'failed') {
              clearInterval(pollInterval);
              alert(`Error generating ${type}: ${job.error}`);
              setIsGenerating(false);
              setActiveType('');
            }
          } catch (error) {
            clearInterval(pollInterval);
            console.error('Error checking job status:', error);
            alert('Error checking generation status. Please try again.');
            setIsGenerating(false);
            setActiveType('');
          }
        }, 3000); // Poll every 3 seconds
      } else {
        // Regular synchronous generation
        setGeneratedContent(response.data);
        setIsGenerating(false);
        setActiveType('');
      }
    } catch (error) {
      console.error('Error generating content:', error);
      alert('Error generating content. Please try again.');
      setIsGenerating(false);
      setActiveType('');
    }
  };

  const downloadContent = async () => {
    if (!generatedContent) return;

    try {
      // Determine file extension based on content type
      let fileExtension = 'txt';
      let filenamePrefix = generatedContent.type;

      if (generatedContent.type === 'slides') {
        fileExtension = 'pptx';
        filenamePrefix = 'presentation';
      } else if (generatedContent.type === 'summary') {
        fileExtension = 'docx';
        filenamePrefix = 'executive-summary';
      } else if (generatedContent.type === 'policy-brief') {
        fileExtension = 'docx';
        filenamePrefix = 'policy-brief';
      } else if (generatedContent.type === 'risk-assessment') {
        fileExtension = 'docx';
        filenamePrefix = 'risk-assessment';
      } else if (generatedContent.type === 'flashcards') {
        fileExtension = 'txt';
        filenamePrefix = 'flashcards';
      } else if (generatedContent.type === 'insights') {
        fileExtension = 'md';
        filenamePrefix = 'insights';
      } else if (generatedContent.type === 'audio-overview') {
        fileExtension = 'mp3';
        filenamePrefix = 'audio-overview';
      } else if (generatedContent.type === 'smartbook') {
        fileExtension = 'mp3';
        filenamePrefix = 'smartbook';
      }

      const filename = `${filenamePrefix}-${new Date().toISOString().split('T')[0]}.${fileExtension}`;

      const response = await axios.post(
        `/api/notebooks/${notebookId}/download/${generatedContent.type}`,
        {
          content: generatedContent.content,
          filename: filename,
        },
        {
          responseType: 'blob',
        }
      );

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading content:', error);
      alert('Error downloading content. Please try again.');
    }
  };

  return (
    <div className="space-y-4">
      {/* Generation Buttons */}
      <div className="grid grid-cols-2 gap-2">
        {contentTypes.map((type) => {
          const Icon = type.icon;
          const isActive = activeType === type.id;

          return (
            <button
              key={type.id}
              onClick={() => generateContent(type.id)}
              disabled={isGenerating || documentsCount === 0}
              className={`${type.color} p-2 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex flex-col items-center gap-2 text-center text-xs shadow-soft min-h-[80px]`}
            >
              {isActive && isGenerating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Icon className="w-4 h-4" />
              )}
              <div>
                <h4 className="font-medium leading-tight">{type.title}</h4>
              </div>
            </button>
          );
        })}
      </div>

      {documentsCount === 0 && (
        <div className="p-3 bg-primary-50 border border-primary-200 rounded-lg">
          <p className="text-primary-800 text-xs">
            📄 Add sources first to enable generation
          </p>
        </div>
      )}

      {/* Generated Content Display */}
      {generatedContent && (
        <div className="bg-white rounded-lg border border-neutral-200 shadow-soft overflow-hidden">
          <div className="p-3 border-b border-neutral-200 flex items-center justify-between">
            <h4 className="text-sm font-medium text-neutral-900 capitalize">
              {generatedContent.type}
            </h4>
            <button
              onClick={downloadContent}
              className="btn-ghost text-xs flex items-center gap-1"
            >
              <Download className="w-3 h-3" />
              Download
            </button>
          </div>

          <div className="p-3 max-h-64 overflow-y-auto scrollbar-custom">
            {(generatedContent.type === 'audio-overview' || generatedContent.type === 'smartbook') ? (
              <div className="space-y-3">
                <audio
                  controls
                  className="w-full"
                  src={`http://localhost:4001${generatedContent.content}`}
                >
                  Your browser does not support the audio element.
                </audio>
                {(generatedContent as any).script && (
                  <div className="pt-3 border-t border-neutral-200">
                    <p className="text-xs font-medium text-neutral-600 mb-2">
                      {generatedContent.type === 'smartbook' ? 'SmartBook Script:' : 'Podcast Script:'}
                    </p>
                    <div className="text-xs text-neutral-700 max-h-40 overflow-y-auto space-y-2">
                      {Array.isArray((generatedContent as any).script) ? (
                        (generatedContent as any).script.map((segment: any, idx: number) => (
                          <div key={idx} className="flex gap-2">
                            <span className="font-semibold">
                              {generatedContent.type === 'smartbook' ? 'Narrator:' : (segment.speaker === 'A' ? 'Host:' : 'Co-host:')}
                            </span>
                            <span>{segment.text}</span>
                          </div>
                        ))
                      ) : (
                        <div className="whitespace-pre-wrap">{(generatedContent as any).script}</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <ReactMarkdown className="prose prose-xs text-neutral-700 max-w-none">
                {generatedContent.content}
              </ReactMarkdown>
            )}
          </div>

          <div className="px-3 py-2 bg-neutral-50 text-xs text-neutral-500">
            Generated from {generatedContent.documentCount} source{generatedContent.documentCount !== 1 ? 's' : ''}
          </div>
        </div>
      )}

      {/* Loading State */}
      {isGenerating && (
        <div className="bg-white rounded-lg border border-neutral-200 p-4 text-center">
          <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-primary-600" />
          <p className="text-xs text-neutral-600">
            Generating {activeType}...
          </p>
        </div>
      )}

      {/* Language Selection Modal */}
      {showLanguageSelect && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold mb-4 text-neutral-900">
              {activeType === 'smartbook' ? 'Select SmartBook Language' : 'Select Podcast Language'}
            </h3>
            <p className="text-sm text-neutral-600 mb-6">
              {activeType === 'smartbook'
                ? 'Choose the language for your educational audiobook:'
                : 'Choose the language for your AI-generated podcast:'}
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => generateContent(activeType, 'en')}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-3 px-4 rounded-lg font-medium transition-colors"
              >
                English
              </button>
              <button
                onClick={() => generateContent(activeType, 'ar')}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-3 px-4 rounded-lg font-medium transition-colors"
              >
                Arabic
              </button>
            </div>
            <button
              onClick={() => {
                setShowLanguageSelect(false);
                setActiveType('');
              }}
              className="w-full mt-3 text-neutral-500 hover:text-neutral-700 text-sm py-2"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}