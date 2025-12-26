'use client';

import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, User } from 'lucide-react';

interface Person {
  id: string;
  label?: string;
  full_name?: string;
  name?: string;
  name_eng?: string;
  name_arabic?: string;
  dob?: string;
  date_of_birth?: string;
  unified_id?: string;
  passport_no?: string;
  passport?: string;
  contact_no?: string;
  nationality?: string;
  gender?: string;
  sex?: string;
  national_id?: string;
  kin?: string;
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
    siblings: true,
    children: true,
  });

  // When selectedNode changes, auto-expand relevant sections
  useEffect(() => {
    if (selectedNode) {
      setExpandedSections({
        personal: true,
        parents: true,
        spouses: true,
        siblings: true,
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
      } else if (type === 'SIBLING_OF') {
        // Sibling relationships (bidirectional)
        if (edge.source === personId) {
          const sibling = idMap.get(edge.target);
          if (sibling) siblings.push(sibling);
        }
        if (edge.target === personId) {
          const sibling = idMap.get(edge.source);
          if (sibling) siblings.push(sibling);
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

  /**
   * Get avatar URL based on person type and gender
   * Citizens use one set of icons, residents use another
   */
  const getAvatarUrl = (person: Person) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const isCitizen = person.person_type === 'citizen' || 
                      (person.person_type === undefined && person.national_id);
    const isFemale = String(person.sex).toUpperCase() === 'F';
    
    // For now, using same icons but structure allows for different resident icons
    // You can replace these paths with different icons for residents
    if (isCitizen) {
      return isFemale 
        ? `${apiUrl}/static/img/citizen/female_icon.jpg`
        : `${apiUrl}/static/img/citizen/male_icon.jpg`;
    } else {
      // Resident icons (currently same, but you can change these paths)
      return isFemale 
        ? `${apiUrl}/static/img/resident/female.png`  // Can be resident_female_icon.jpg
        : `${apiUrl}/static/img/resident/male.png`;   // Can be resident_male_icon.jpg
    }
  };

  /**
   * Render a person card with all production meta fields
   * Field order: Name (Eng/Arabic) → DOB → Unified ID → Passport → Contact → Nationality → Gender
   */
  const renderPersonCard = (person: Person) => {
    const nameEng = person.name_eng || person.full_name || person.name || person.label || person.id;
    const nameArabic = person.name_arabic;
    const dob = person.dob || person.date_of_birth;
    const unifiedId = person.unified_id || person.id;
    const passportNo = person.passport_no || person.passport;
    const contactNo = person.contact_no;
    const nationality = person.nationality;
    const gender = person.gender || person.sex;
    const kin = person.kin || '';
    
    // Determine if this person is a citizen
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
              src={getAvatarUrl(person)}
              alt={nameEng}
              className="w-full h-full object-cover"
            />
          </div>

          {/* Details - Production meta fields */}
          <div className="flex-1 min-w-0">
            {/* 1. NAME (English) */}
            <h4 className="font-semibold text-neutral-900 text-sm mb-1">
              {nameEng}
            </h4>
            
            {/* 1b. NAME (Arabic) */}
            {nameArabic && (
              <h4 className="font-semibold text-neutral-900 text-sm mb-2">
                {nameArabic}
              </h4>
            )}

            {/* Info items - Production fields */}
            <div className="space-y-1.5 text-xs text-neutral-600">
              
              {/* 2. PERSON TYPE */}
              {person.person_type && (
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 text-xs font-medium rounded inline-block ${
                    person.person_type === 'citizen' 
                      ? 'bg-[#DAA520] text-white' 
                      : 'bg-green-100 text-green-700'
                  }`}>
                    {person.person_type === 'citizen' ? 'Citizen' : 'Resident'}
                  </span>
                </div>
              )}
              
              {/* 3. KIN RELATIONSHIP */}
              {kin && (
                <div className="flex items-center gap-2">
                  <span className="text-neutral-500 font-medium">Relation:</span>
                  <span className="capitalize font-medium text-neutral-700">{kin}</span>
                </div>
              )}
              
              {/* 4. DATE OF BIRTH */}
              {dob && (
                <div className="flex items-center gap-2">
                  <span className="text-neutral-500 font-medium">DOB:</span>
                  <span className="font-mono">{dob}</span>
                </div>
              )}

              {/* 5. UNIFIED ID */}
              {unifiedId && (
                <div className="flex items-center gap-2">
                  <span className="text-neutral-500 font-medium">Unified ID:</span>
                  <span className="font-mono">{unifiedId}</span>
                </div>
              )}

              {/* 6. PASSPORT NO */}
              {passportNo && (
                <div className="flex items-center gap-2">
                  <span className="text-neutral-500 font-medium">Passport No:</span>
                  <span className="font-mono">{passportNo}</span>
                </div>
              )}

              {/* 7. CONTACT NO */}
              {contactNo && (
                <div className="flex items-center gap-2">
                  <span className="text-neutral-500 font-medium">Contact No:</span>
                  <span>{contactNo}</span>
                </div>
              )}

              {/* 8. NATIONALITY */}
              {nationality && (
                <div className="flex items-center gap-2">
                  <span className="text-neutral-500 font-medium">Nationality:</span>
                  <span>{nationality}</span>
                </div>
              )}

              {/* 9. GENDER */}
              {gender && (
                <div className="flex items-center gap-2">
                  <span className="text-neutral-500 font-medium">Gender:</span>
                  <span>{gender === 'F' || gender === 'Female' ? 'Female' : gender === 'M' || gender === 'Male' ? 'Male' : gender}</span>
                </div>
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
      id: 'siblings',
      title: 'Siblings',
      data: relationships.siblings,
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
    <div className="h-full flex flex-col bg-neutral-50">
      {/* Header - Sticky */}
      <div className="sticky top-0 z-10 bg-white border-b border-neutral-200 px-6 py-4">
        <h3 className="text-lg font-bold text-neutral-900 mb-1">
          Family Details
        </h3>
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-sm text-neutral-600 truncate">
            {fullName}
          </p>
          {/* {isRootPerson && (
            <span className="px-2 py-0.5 bg-[#DAA520] text-white text-xs font-semibold rounded">
              ROOT
            </span>
          )} */}
          {displayPerson.person_type && (
            <span className={`px-2 py-0.5 text-xs font-semibold rounded ${
              displayPerson.person_type === 'citizen'
                ? 'bg-[#DAA520] text-white'
                : 'bg-green-100 text-green-700'
            }`}>
              {displayPerson.person_type === 'citizen' ? 'Citizen' : 'Resident'}
            </span>
          )}
        </div>
      </div>

      {/* Scrollable Accordion Sections */}
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
