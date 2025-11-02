'use client';

import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, User } from 'lucide-react';

interface Person {
  id: string;
  label?: string;
  full_name?: string;
  name?: string;
  sex?: string;
  kin?: string;
  national_id?: string;
  passport?: string;
  date_of_birth?: string;
  person_type?: 'citizen' | 'resident';
}

interface TreeData {
  root: string;
  nodes: Person[];
  edges: any[];
}

interface FamilyDetailsProps {
  treeData: TreeData | null;
  selectedNode?: Person | null;
  personId: string;
  profileType: 'citizens' | 'residents';
}

export default function FamilyDetails({ 
  treeData, 
  selectedNode,
  personId,
  profileType 
}: FamilyDetailsProps) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    personal: true,
    parents: true,
    spouses: true,
    children: true,
  });

  // When selectedNode changes, auto-expand relevant sections
  useEffect(() => {
    if (selectedNode) {
      setExpandedSections({
        personal: true,
        parents: true,
        spouses: true,
        children: true,
      });
    }
  }, [selectedNode?.id]);

  if (!treeData) {
    return (
      <div className="h-full flex flex-col">
        <div className="sticky top-0 z-10 bg-white border-b border-neutral-200 px-6 py-4">
          <h3 className="text-lg font-bold text-neutral-900 mb-1">Family Details</h3>
          <p className="text-sm text-neutral-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Get the person to display (selected node or root)
  const displayPerson = selectedNode || treeData.nodes.find(n => n.id === personId) || treeData.nodes[0];

  if (!displayPerson) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-neutral-100 flex items-center justify-center mx-auto mb-4">
            <User className="w-8 h-8 text-neutral-400" />
          </div>
          <p className="text-neutral-600 text-sm">No person selected</p>
        </div>
      </div>
    );
  }

  // Build adjacency maps for relationships
  const buildRelationships = (personId: string) => {
    const parents: Person[] = [];
    const children: Person[] = [];
    const spouses: Person[] = [];
    const siblings: Person[] = [];

    const idMap = new Map(treeData.nodes.map(n => [n.id, n]));

    treeData.edges?.forEach((edge: any) => {
      if (!edge || !edge.source || !edge.target) return;
      const type = String(edge.type || '').toUpperCase();

      if (type === 'CHILD_OF') {
        // personId is the child -> target is parent
        if (edge.source === personId) {
          const parent = idMap.get(edge.target);
          if (parent) parents.push(parent);
        }
        // personId is the parent -> source is child
        if (edge.target === personId) {
          const child = idMap.get(edge.source);
          if (child) children.push(child);
        }
      } else if (type === 'SPOUSE_OF') {
        if (edge.source === personId) {
          const spouse = idMap.get(edge.target);
          if (spouse) spouses.push(spouse);
        }
        if (edge.target === personId) {
          const spouse = idMap.get(edge.source);
          if (spouse) spouses.push(spouse);
        }
      }
    });

    return { parents, children, spouses, siblings };
  };

  const relationships = buildRelationships(displayPerson.id);

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const getAvatarUrl = (sex?: string) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    if (String(sex).toUpperCase() === 'F') {
      return `${apiUrl}/static/img/female_icon.jpg`;
    }
    return `${apiUrl}/static/img/male_icon.jpg`;
  };

  /**
   * Render a person card with conditional metadata based on person_type
   * 
   * Citizens show:
   * - Full name
   * - Gender
   * - Kin relationship
   * - Date of birth
   * - National ID (if present)
   * - Passport (if present)
   * 
   * Residents show:
   * - Full name
   * - Gender
   * - Kin relationship
   * - Date of birth
   */
  const renderPersonCard = (person: Person) => {
    const fullName = person.full_name || person.name || person.label || person.id;
    const kin = person.kin || '';
    
    // Determine if this person is a citizen based on person_type
    // Fallback to checking if national_id exists
    const isCitizen = person.person_type === 'citizen' || 
                      (person.person_type === undefined && person.national_id);

    return (
      <div
        key={person.id}
        className="bg-white rounded-lg border border-neutral-200 p-4 hover:shadow-md transition-shadow"
      >
        <div className="flex items-start gap-3">
          {/* Avatar */}
          <div className="w-12 h-12 rounded-lg bg-primary-100 flex items-center justify-center flex-shrink-0 overflow-hidden">
            <img
              src={getAvatarUrl(person.sex)}
              alt={fullName}
              className="w-full h-full object-cover"
            />
          </div>

          {/* Details */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h4 className="font-semibold text-neutral-900 truncate">
                {fullName}
              </h4>
              {/* Person type badge */}
              {person.person_type && (
                <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                  person.person_type === 'citizen' 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'bg-green-100 text-green-700'
                }`}>
                  {person.person_type === 'citizen' ? 'Citizen' : 'Resident'}
                </span>
              )}
            </div>

            {/* Info items - Always shown fields */}
            <div className="space-y-1.5 text-xs text-neutral-600">
              {/* Gender - Always shown */}
              {person.sex && (
                <div className="flex items-center gap-2">
                  <User className="w-3.5 h-3.5 text-neutral-400" />
                  <span>{person.sex === 'F' ? 'Female' : 'Male'}</span>
                </div>
              )}
              
              {/* Date of Birth - Always shown */}
              {person.date_of_birth && (
                <div className="flex items-center gap-2">
                  <span>📅</span>
                  <span>{person.date_of_birth}</span>
                </div>
              )}
              
              {/* Kin Relationship - Always shown */}
              {kin && (
                <div className="mt-2 inline-block px-2 py-1 bg-neutral-100 rounded text-xs font-medium text-neutral-700">
                  {kin}
                </div>
              )}
              
              {/* CONDITIONAL FIELDS - Only for Citizens */}
              {isCitizen && (
                <>
                  {/* National ID - Citizens only */}
                  {person.national_id && (
                    <div className="flex items-center gap-2">
                      <User className="w-3.5 h-3.5 text-neutral-400" />
                      <span className="font-mono text-xs">{person.national_id}</span>
                    </div>
                  )}
                  
                  {/* Passport - Citizens only (if present) */}
                  {person.passport && (
                    <div className="flex items-center gap-2">
                      <span>🛂</span>
                      <span className="font-mono text-xs">{person.passport}</span>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const sections = [
    {
      id: 'personal',
      title: 'Personal Information',
      data: [displayPerson],
    },
    {
      id: 'parents',
      title: 'Parents',
      data: relationships.parents,
    },
    {
      id: 'spouses',
      title: 'Spouses',
      data: relationships.spouses,
    },
    {
      id: 'children',
      title: 'Children',
      data: relationships.children,
    },
  ];

  const fullName = displayPerson.full_name || displayPerson.name || displayPerson.label || displayPerson.id;
  const isRootPerson = displayPerson.id === personId;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white border-b border-neutral-200 px-6 py-4">
        <h3 className="text-lg font-bold text-neutral-900 mb-1">
          Family Details
        </h3>
        <div className="flex items-center gap-2">
          <p className="text-sm text-neutral-600 truncate">
            {fullName}
          </p>
          {isRootPerson && (
            <span className="px-2 py-0.5 bg-[#DAA520] text-white text-xs font-semibold rounded">
              ROOT
            </span>
          )}
          {displayPerson.person_type && (
            <span className={`px-2 py-0.5 text-xs font-semibold rounded ${
              displayPerson.person_type === 'citizen'
                ? 'bg-blue-100 text-blue-700'
                : 'bg-green-100 text-green-700'
            }`}>
              {displayPerson.person_type === 'citizen' ? 'CITIZEN' : 'RESIDENT'}
            </span>
          )}
        </div>
      </div>

      {/* Accordion Sections */}
      <div className="flex-1 overflow-y-auto p-6 space-y-3">
        {sections.map((section) => {
          const isExpanded = expandedSections[section.id];
          const hasData = section.data && section.data.length > 0;

          return (
            <div key={section.id} className="bg-white rounded-lg border border-neutral-200 overflow-hidden">
              {/* Section Header */}
              <button
                onClick={() => toggleSection(section.id)}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-neutral-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-neutral-900">
                    {section.title}
                  </span>
                  <span className="text-xs text-neutral-500 bg-neutral-100 px-2 py-0.5 rounded-full">
                    {section.data?.length || 0}
                  </span>
                </div>
                {isExpanded ? (
                  <ChevronUp className="w-5 h-5 text-neutral-400" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-neutral-400" />
                )}
              </button>

              {/* Section Content */}
              {isExpanded && (
                <div className="px-4 pb-4 space-y-3">
                  {!hasData ? (
                    <p className="text-sm text-neutral-500 text-center py-4">
                      No data available
                    </p>
                  ) : (
                    section.data.map(renderPersonCard)
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
