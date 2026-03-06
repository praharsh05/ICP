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
  
  // State for tracking current root and selected node
  const [currentPersonId, setCurrentPersonId] = useState(personId);
  const [selectedNode, setSelectedNode] = useState<any>(null);

  useEffect(() => {
    const fetchTreeData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(
          `${apiUrl}/api/v1/persons/${currentPersonId}/tree?depth=3`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch tree data');
        }

        const data = await response.json();
        setTreeData(data);
        
        // Set the current person as selected node
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
  }, [currentPersonId]);

  // Handler for when user clicks a card to navigate to new person
  const handlePersonSelect = (newPersonId: string) => {
    // Update URL without page reload
    router.push(`/tree/${newPersonId}?type=${profileType}`, { scroll: false });
    
    // Update state to trigger data fetch
    setCurrentPersonId(newPersonId);
  };

  // Handler for when user clicks a card just to view details
  const handleNodeClick = (nodeId: string) => {
    const node = treeData?.nodes?.find((n: any) => n.id === nodeId);
    if (node) {
      setSelectedNode(node);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-white">
      {/* Header - Fixed height */}
      <header className="sticky top-0 z-50 bg-white border-b border-neutral-200 h-16 flex-shrink-0">
        <div className="h-full max-w-full px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-full">
            <button
              onClick={() => router.push('/landing')}
              className="flex items-center gap-2 text-neutral-600 hover:text-neutral-900 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
              <span className="font-medium">Back</span>
            </button>
            
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-semibold text-[#DAA520]">
                Family Tree of {currentPersonId}
              </h1>
              {/* <span className="text-xl font-semibold text-[#DAA520]">
                ({currentPersonId})
              </span> */}
            </div>
            
            <div className="w-24"></div> {/* Spacer for center alignment */}
          </div>
        </div>
      </header>

      {/* Main Content - Takes remaining height */}
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
            {/* Family Details Section - 30% width, vertically scrollable */}
            <div 
              className="w-[30%] flex-shrink-0 overflow-y-auto bg-neutral-50 border-r border-neutral-200"
              style={{ 
                height: 'calc(100vh - 4rem - 3.5rem)' // screen height - header (4rem) - footer (3.5rem)
              }}
            >
              <FamilyDetails 
                treeData={treeData}
                selectedNode={selectedNode}
                personId={currentPersonId}
                profileType={profileType}
              />
            </div>

            {/* Graph Section - 70% width, fixed height */}
            <div 
              className="w-[70%] flex-shrink-0 relative bg-white"
              style={{ 
                height: 'calc(100vh - 4rem - 3.5rem)' // screen height - header (4rem) - footer (3.5rem)
              }}
            >
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

      {/* Footer - Fixed height */}
      <footer className="bg-neutral-50 border-t border-neutral-200 py-4 flex-shrink-0 h-14">
        <div className="h-full max-w-full px-4 sm:px-6 lg:px-8 flex items-center">
          <p className="text-center text-sm text-neutral-600 w-full">
            © 2026 Xpress Innovation
          </p>
        </div>
      </footer>
    </div>
  );
}
