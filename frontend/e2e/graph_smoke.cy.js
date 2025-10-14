describe('Family Graph',()=>{ it('loads',()=>{ cy.visit('/'); cy.contains('Family Graph').should('exist'); }); });
