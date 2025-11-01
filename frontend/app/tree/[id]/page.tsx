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
  const profileType = (searchParams.get('type') || 'citizens') as 'citizens' | 'residents';
  const [treeData, setTreeData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // NEW: State for tracking current root and selected node
  const [currentPersonId, setCurrentPersonId] = useState(personId);
  const [selectedNode, setSelectedNode] = useState<any>(null);

  useEffect(() => {
    const fetchTreeData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(
          `${apiUrl}/api/v1/persons/${currentPersonId}/tree?depth=3&lang=en`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch tree data');
        }

        const data = await response.json();
        setTreeData(data);
        
        // NEW: Set the current person as selected node
        const currentNode = data.nodes?.find((n: any) => n.id === currentPersonId);
        setSelectedNode(currentNode || data.nodes?.[0]);
        
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    if (currentPersonId) {
      fetchTreeData();
    }
  }, [currentPersonId]); // NEW: Depend on currentPersonId instead of personId

  // NEW: Handler for when user clicks a card to navigate to new person
  const handlePersonSelect = (newPersonId: string) => {
    // Update URL without page reload
    router.push(`/tree/${newPersonId}?type=${profileType}`, { scroll: false });
    
    // Update state to trigger data fetch
    setCurrentPersonId(newPersonId);
  };

  // NEW: Handler for when user clicks a card just to view details
  const handleNodeClick = (nodeId: string) => {
    const node = treeData?.nodes?.find((n: any) => n.id === nodeId);
    if (node) {
      setSelectedNode(node);
    }
  };

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
            
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-semibold text-[#DAA520]">
                Family Tree
              </h1>
              {/* NEW: Show current person ID */}
              <span className="text-sm text-neutral-500">
                ({currentPersonId})
              </span>
            </div>
            
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
            {/* Family Details Section - 25% */}
            <div className="flex-[1] overflow-y-auto bg-neutral-50">
              <FamilyDetails 
                treeData={treeData}
                selectedNode={selectedNode}
                personId={currentPersonId}
                profileType={profileType}
              />
            </div>

            {/* Graph Section - 75% */}
            <div className="flex-[3] border-l border-neutral-200 relative" style={{ minHeight: '600px' }}>
              <FamilyGraph 
                treeData={treeData} 
                personId={currentPersonId}
                onPersonSelect={handlePersonSelect}
                onNodeClick={handleNodeClick}
              />
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