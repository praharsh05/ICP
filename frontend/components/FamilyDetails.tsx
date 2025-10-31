'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface Person {
  id: string;
  label: string;
  sex?: string;
  kin?: string;
  full_name?: string;
  name?: string;
  life_status?: string;
  national_id?: string;
  passport?: string;
}

interface TreeData {
  root: string;
  nodes: Person[];
  edges: any[];
}

interface FamilyDetailsProps {
  treeData: TreeData | null;
}

export default function FamilyDetails({ treeData }: FamilyDetailsProps) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    Self: true,
    Parents: true,
    Children: true,
  });

  if (!treeData) {
    return (
      <div className="p-6">
        <h2 className="text-2xl font-bold text-[#DAA520] mb-4">Family Details</h2>
        <p className="text-neutral-500">No data available</p>
      </div>
    );
  }

  // Group nodes by relationship
  const groupNodes = () => {
    const nodes = treeData.nodes || [];
    const groups: Record<string, Person[]> = {
      Self: [],
      Parents: [],
      Children: [],
      Spouses: [],
      Siblings: [],
      Grandparents: [],
      Grandchildren: [],
      'In-laws': [],
    };

    nodes.forEach((node) => {
      const kin = String(node.kin || '').toLowerCase();

      if (kin === 'self') {
        groups.Self.push(node);
      } else if (['father', 'mother', 'parent'].includes(kin)) {
        groups.Parents.push(node);
      } else if (['son', 'daughter', 'child'].includes(kin)) {
        groups.Children.push(node);
      } else if (['husband', 'wife', 'spouse'].includes(kin)) {
        groups.Spouses.push(node);
      } else if (['brother', 'sister', 'sibling'].includes(kin)) {
        groups.Siblings.push(node);
      } else if (kin.includes('grandfather') || kin.includes('grandmother') || kin.includes('grandparent')) {
        groups.Grandparents.push(node);
      } else if (['grandson', 'granddaughter', 'grandchild'].includes(kin)) {
        groups.Grandchildren.push(node);
      } else if (kin.includes('in-law') || kin.includes('in law')) {
        groups['In-laws'].push(node);
      }
    });

    return groups;
  };

  const groups = groupNodes();

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

  const renderPersonCard = (person: Person, isSelf: boolean = false) => {
    const fullName = person.full_name || person.name || person.label || person.id;
    const kin = person.kin || '';

    return (
      <div
        key={person.id}
        className={`flex items-center gap-3 p-3 rounded-lg border transition-all ${
          isSelf
            ? 'border-[#DAA520] bg-[#FFFAF0] shadow-md'
            : 'border-neutral-200 bg-white hover:border-neutral-300'
        }`}
      >
        <div className="w-10 h-10 rounded-lg overflow-hidden bg-neutral-100 flex-shrink-0">
          <img
            src={getAvatarUrl(person.sex)}
            alt={fullName}
            className="w-full h-full object-cover"
          />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs text-neutral-500 mb-1">{kin}</div>
          <div className="font-semibold text-sm text-neutral-900 truncate">
            {fullName}
          </div>
        </div>
      </div>
    );
  };

  const order = ['Self', 'Parents', 'Children', 'Spouses', 'Siblings', 'Grandparents', 'Grandchildren', 'In-laws'];

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold text-[#DAA520] mb-6">Family Details</h2>

      <div className="space-y-3">
        {order.map((section) => {
          const people = groups[section] || [];
          if (people.length === 0) return null;

          const isExpanded = expandedSections[section];

          return (
            <div key={section} className="border border-neutral-200 rounded-lg overflow-hidden">
              <button
                onClick={() => toggleSection(section)}
                className="w-full flex items-center justify-between p-4 bg-neutral-50 hover:bg-neutral-100 transition-colors"
              >
                <span className="font-semibold text-neutral-900">
                  {section} ({people.length})
                </span>
                {isExpanded ? (
                  <ChevronUp className="w-5 h-5 text-neutral-600" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-neutral-600" />
                )}
              </button>

              {isExpanded && (
                <div className="p-4 space-y-2">
                  {people.map((person) =>
                    renderPersonCard(person, section === 'Self')
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
