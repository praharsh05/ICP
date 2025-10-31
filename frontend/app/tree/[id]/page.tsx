'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import FamilyGraph from '../../../components/FamilyGraph';
import FamilyDetails from '../../../components/FamilyDetails';

export default function TreePage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const personId = params.id as string;
  const profileType = searchParams.get('type') || 'citizens';

  const [treeData, setTreeData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTreeData = async () => {
      try {
        setLoading(true);
        setError(null);

        // API URL from backend
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(
          `${apiUrl}/api/v1/persons/${personId}/tree?depth=3&lang=en`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch tree data');
        }

        const data = await response.json();
        setTreeData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    if (personId) {
      fetchTreeData();
    }
  }, [personId]);

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white border-b border-neutral-200">
        <div className="max-w-full px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <button
              onClick={() => router.push('/landing')}
              className="flex items-center gap-2 text-neutral-600 hover:text-neutral-900 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
              <span className="font-medium">Back</span>
            </button>

            <h1 className="text-xl font-semibold text-[#DAA520]">
              Family Tree
            </h1>

            <div className="w-24"></div> {/* Spacer for center alignment */}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex overflow-hidden">
        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
              <p className="text-neutral-600">Loading family tree...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center max-w-md">
              <p className="text-red-600 mb-4">{error}</p>
              <button
                onClick={() => router.push('/landing')}
                className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-2 rounded-lg"
              >
                Go Back
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* Graph Section - 75% */}
            <div className="flex-[3] border-r border-neutral-200">
              <FamilyGraph treeData={treeData} personId={personId} />
            </div>

            {/* Family Details Section - 25% */}
            <div className="flex-[1] overflow-y-auto">
              <FamilyDetails treeData={treeData} />
            </div>
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-neutral-50 border-t border-neutral-200 py-4">
        <div className="max-w-full px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-neutral-600">
            © 2025 Intelligence & Community Platform
          </p>
        </div>
      </footer>
    </div>
  );
}
