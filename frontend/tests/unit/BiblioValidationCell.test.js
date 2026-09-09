/**
 * Tests pour le composant BiblioValidationCell
 * Affiche les statuts de validation bibliographique avec indicateurs visuels
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import BiblioValidationCell from '../../src/components/BiblioValidationCell.vue';

// Mock the BiblioValidationService
vi.mock('../../src/services/BiblioValidationService.js', () => ({
  BiblioValidationService: vi.fn().mockImplementation(() => ({
    validateBiblio: vi.fn()
  }))
}));

describe('BiblioValidationCell', () => {
  let wrapper;

  const defaultProps = {
    author: 'Michel Houellebecq',
    title: 'Les Particules élémentaires',
    publisher: 'Flammarion'
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  describe('Initial state (loading)', () => {
    it('should display loading indicator when validation is in progress', async () => {
      const { BiblioValidationService } = await import('../../src/services/BiblioValidationService.js');

      // Mock a slow response to test loading state
      const mockService = {
        validateBiblio: vi.fn().mockImplementation(() =>
          new Promise(resolve => setTimeout(() => resolve({
            status: 'verified',
            data: {
              original: { author: 'Michel Houellebecq', title: 'Les Particules élémentaires' },
              source: 'babelio'
            }
          }), 100))
        )
      };
      BiblioValidationService.mockImplementation(() => mockService);

      wrapper = mount(BiblioValidationCell, {
        props: defaultProps
      });

      // Wait for component to mount and start validation
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-testid="validation-loading"]').exists()).toBe(true);
      expect(wrapper.text()).toContain('Vérification...');
    });

    it('should show validation starting automatically on mount', async () => {
      const { BiblioValidationService } = await import('../../src/services/BiblioValidationService.js');

      const mockService = {
        validateBiblio: vi.fn().mockResolvedValue({
          status: 'verified',
          data: {
            original: { author: 'Michel Houellebecq', title: 'Les Particules élémentaires' },
            source: 'babelio'
          }
        })
      };
      BiblioValidationService.mockImplementation(() => mockService);

      wrapper = mount(BiblioValidationCell, {
        props: defaultProps
      });

      // Wait for mounted lifecycle
      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 50));

      // Should start validation on mount
      expect(mockService.validateBiblio).toHaveBeenCalledWith(
        'Michel Houellebecq',
        'Les Particules élémentaires',
        'Flammarion',
        null
      );
    });
  });

  describe('Success states', () => {
    it('should display perfect match indicator for verified author and book', async () => {
      const { BiblioValidationService } = await import('../../src/services/BiblioValidationService.js');

      const mockService = {
        validateBiblio: vi.fn().mockResolvedValue({
          status: 'verified',
          data: {
            original: {
              author: 'Michel Houellebecq',
              title: 'Les Particules élémentaires',
              publisher: 'Flammarion'
            },
            source: 'babelio',
            confidence_score: 1.0
          }
        })
      };
      BiblioValidationService.mockImplementation(() => mockService);

      wrapper = mount(BiblioValidationCell, {
        props: defaultProps
      });

      // Wait for validation to complete
      await new Promise(resolve => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-testid="validation-success"]').exists()).toBe(true);
      expect(wrapper.text()).toContain('✅');
      expect(wrapper.text()).toContain('Validé');
    });

    it('should display suggestion for corrected author verified by book', async () => {
      const { BiblioValidationService } = await import('../../src/services/BiblioValidationService.js');

      const mockService = {
        validateBiblio: vi.fn().mockResolvedValue({
          status: 'suggestion',
          data: {
            original: {
              author: 'Michel Houellebeck',
              title: 'Les Particules élémentaires',
              publisher: 'Flammarion'
            },
            suggested: {
              author: 'Michel Houellebecq',
              title: 'Les Particules élémentaires'
            },
            corrections: {
              author: true,
              title: false
            },
            source: 'babelio',
            confidence_score: 0.9
          }
        })
      };
      BiblioValidationService.mockImplementation(() => mockService);

      wrapper = mount(BiblioValidationCell, {
        props: { ...defaultProps, author: 'Michel Houellebeck' }
      });

      // Wait for validation to complete
      await new Promise(resolve => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-testid="validation-suggestion"]').exists()).toBe(true);
      expect(wrapper.text()).toContain('🔄');
      expect(wrapper.text()).toContain('Michel Houellebecq');
      expect(wrapper.text()).toContain('Suggestion');
    });

    it('should display not found indicator when no match exists', async () => {
      const { BiblioValidationService } = await import('../../src/services/BiblioValidationService.js');

      const mockService = {
        validateBiblio: vi.fn().mockResolvedValue({
          status: 'not_found',
          data: {
            original: {
              author: 'Auteur Inexistant',
              title: 'Titre Inexistant',
              publisher: 'Éditeur'
            },
            reason: 'no_reliable_match_found',
            attempts: ['babelio']
          }
        })
      };
      BiblioValidationService.mockImplementation(() => mockService);

      wrapper = mount(BiblioValidationCell, {
        props: { ...defaultProps, author: 'Auteur Inexistant', title: 'Titre Inexistant' }
      });

      // Wait for validation to complete
      await new Promise(resolve => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-testid="validation-not-found"]').exists()).toBe(true);
      expect(wrapper.text()).toContain('❓');
      expect(wrapper.text()).toContain('Non trouvé');
    });
  });

  describe('Error handling', () => {
    it('should display error indicator when verification fails', async () => {
      // Mock console.error to avoid polluting test logs
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // Mock the validateBiblio method to reject before mounting
      const { BiblioValidationService } = await import('../../src/services/BiblioValidationService.js');
      BiblioValidationService.mockImplementation(() => ({
        validateBiblio: vi.fn().mockRejectedValue(new Error('Network error'))
      }));

      wrapper = mount(BiblioValidationCell, {
        props: defaultProps
      });

      // Wait for validation to complete
      await new Promise(resolve => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-testid="validation-error"]').exists()).toBe(true);
      expect(wrapper.text()).toContain('⚠️');
      expect(wrapper.text()).toContain('Erreur');

      // Verify the error was logged (but silently)
      expect(consoleSpy).toHaveBeenCalledWith('Erreur de vérification Babelio:', expect.any(Error));

      consoleSpy.mockRestore();
    });

    it('should provide retry functionality on error', async () => {
      // Mock console.error to avoid polluting test logs
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // Mock the validateBiblio method to reject initially, then succeed on retry
      const { BiblioValidationService } = await import('../../src/services/BiblioValidationService.js');
      const mockValidateBiblio = vi.fn().mockRejectedValue(new Error('Network error'));

      BiblioValidationService.mockImplementation(() => ({
        validateBiblio: mockValidateBiblio
      }));

      wrapper = mount(BiblioValidationCell, {
        props: defaultProps
      });

      // Wait for initial error
      await new Promise(resolve => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();

      const retryButton = wrapper.find('[data-testid="retry-button"]');
      expect(retryButton.exists()).toBe(true);

      // Mock successful retry
      mockValidateBiblio.mockClear();
      mockValidateBiblio.mockResolvedValue({
        status: 'verified',
        data: {
          original: {
            author: 'Michel Houellebecq',
            title: 'Les Particules élémentaires',
            publisher: 'Flammarion'
          },
          source: 'babelio',
          confidence_score: 1.0
        }
      });

      // Clear the lastValidationTime to avoid rate limiting during retry
      wrapper.vm.lastValidationTime = 0;

      await retryButton.trigger('click');

      // Wait for the retry validation to complete
      await new Promise(resolve => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();

      // Should now show success state
      expect(wrapper.find('[data-testid="validation-success"]').exists()).toBe(true);

      consoleSpy.mockRestore();
    });
  });

  describe('Blocked 403 (Issue #304)', () => {
    it('should display a distinct blocked state (not the generic error state) when Babelio returns blocked_403', async () => {
      const { BiblioValidationService } = await import('../../src/services/BiblioValidationService.js');
      BiblioValidationService.mockImplementation(() => ({
        validateBiblio: vi.fn().mockResolvedValue({
          status: 'blocked_403',
          data: {
            original: { author: 'Michel Houellebecq', title: 'Les Particules élémentaires' },
            reason: 'babelio_blocked_403'
          }
        })
      }));

      wrapper = mount(BiblioValidationCell, {
        props: defaultProps
      });

      await new Promise(resolve => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-testid="validation-blocked-403"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="validation-error"]').exists()).toBe(false);
      expect(wrapper.text()).toContain('403');
    });

    it('should provide a retry button on the blocked_403 state', async () => {
      const { BiblioValidationService } = await import('../../src/services/BiblioValidationService.js');
      const mockValidateBiblio = vi.fn().mockResolvedValue({
        status: 'blocked_403',
        data: {
          original: { author: 'Michel Houellebecq', title: 'Les Particules élémentaires' },
          reason: 'babelio_blocked_403'
        }
      });

      BiblioValidationService.mockImplementation(() => ({
        validateBiblio: mockValidateBiblio
      }));

      wrapper = mount(BiblioValidationCell, {
        props: defaultProps
      });

      await new Promise(resolve => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();

      const retryButton = wrapper.find('[data-testid="validation-blocked-403"] [data-testid="retry-button"]');
      expect(retryButton.exists()).toBe(true);

      mockValidateBiblio.mockClear();
      mockValidateBiblio.mockResolvedValue({
        status: 'verified',
        data: {
          original: {
            author: 'Michel Houellebecq',
            title: 'Les Particules élémentaires',
            publisher: 'Flammarion'
          },
          source: 'babelio',
          confidence_score: 1.0
        }
      });

      wrapper.vm.lastValidationTime = 0;
      await retryButton.trigger('click');

      await new Promise(resolve => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-testid="validation-success"]').exists()).toBe(true);
    });
  });

  describe('Rate limiting', () => {
    it('should respect rate limiting by delaying verification', async () => {
      wrapper = mount(BiblioValidationCell, {
        props: defaultProps
      });

      // Set lastValidationTime to simulate recent call
      wrapper.vm.lastValidationTime = Date.now() - 500; // 500ms ago

      const startTime = Date.now();
      await wrapper.vm.waitForRateLimit();
      const elapsed = Date.now() - startTime;

      // Should wait at least 500ms more to reach 1 second total
      expect(elapsed).toBeGreaterThanOrEqual(400); // Allow some tolerance
    });
  });

  // Book verification is now handled internally by BiblioValidationService

  // This logic is now handled internally by BiblioValidationService

  describe('Props validation', () => {
    it('should handle missing author gracefully', () => {
      wrapper = mount(BiblioValidationCell, {
        props: {
          author: '',
          title: 'Some Title',
          publisher: 'Some Publisher'
        }
      });

      expect(wrapper.exists()).toBe(true);
      expect(wrapper.find('[data-testid="validation-disabled"]').exists()).toBe(true);
    });

    it('should handle missing title gracefully', async () => {
      const { BiblioValidationService } = await import('../../src/services/BiblioValidationService.js');

      const mockService = {
        validateBiblio: vi.fn().mockResolvedValue({
          status: 'verified',
          data: {
            original: {
              author: 'Some Author',
              title: '',
              publisher: 'Some Publisher'
            },
            source: 'babelio',
            confidence_score: 1.0
          }
        })
      };
      BiblioValidationService.mockImplementation(() => mockService);

      wrapper = mount(BiblioValidationCell, {
        props: {
          author: 'Some Author',
          title: '',
          publisher: 'Some Publisher'
        }
      });

      expect(wrapper.exists()).toBe(true);

      // Should start validation despite missing title (author only)
      await new Promise(resolve => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();
      expect(wrapper.find('[data-testid="validation-success"]').exists()).toBe(true);
    });
  });

  describe('Real-world cases with BiblioValidationService (TDD)', () => {
    describe('✅ Validation directe (pas de suggestion)', () => {
      it('should validate directly: Christophe Bigot - Un autre Matin ailleurs', async () => {
        // Given: Real data from /livres-auteurs that is already correct
        const { BiblioValidationService } = await import('../../src/services/BiblioValidationService.js');

        const mockService = {
          validateBiblio: vi.fn().mockResolvedValue({
            status: 'verified',
            data: {
              original: {
                author: 'Christophe Bigot',
                title: 'Un autre Matin ailleurs',
                publisher: 'Éditeur'
              },
              source: 'babelio'
            }
          })
        };
        BiblioValidationService.mockImplementation(() => mockService);

        wrapper = mount(BiblioValidationCell, {
          props: {
            author: 'Christophe Bigot',
            title: 'Un autre Matin ailleurs',
            publisher: 'Éditeur'
          }
        });

        await new Promise(resolve => setTimeout(resolve, 50));
        await wrapper.vm.$nextTick();

        // Should show ✅ Validé (no suggestion needed)
        expect(wrapper.find('[data-testid="validation-success"]').exists()).toBe(true);
        expect(wrapper.text()).toContain('✅');
        expect(wrapper.text()).toContain('Validé');
        expect(wrapper.text()).not.toContain('Suggestion');

        // Verify service was called correctly
        expect(mockService.validateBiblio).toHaveBeenCalledWith(
          'Christophe Bigot',
          'Un autre Matin ailleurs',
          'Éditeur',
          null // no episodeId in this test
        );
      });
    });

    describe('🔄 Suggestion (correction possible)', () => {
      it('should suggest correction: Alain Mabancou -> Alain Mabanckou', async () => {
        // Given: Real data from /livres-auteurs with author typo
        const { BiblioValidationService } = await import('../../src/services/BiblioValidationService.js');

        const mockService = {
          validateBiblio: vi.fn().mockResolvedValue({
            status: 'suggestion',
            data: {
              original: {
                author: 'Alain Mabancou',      // Typo from /livres-auteurs
                title: 'Ramsès de Paris',
                publisher: 'Seuil'
              },
              suggested: {
                author: 'Alain Mabanckou',     // Corrected
                title: 'Ramsès de Paris'       // Unchanged
              },
              corrections: {
                author: true,
                title: false
              },
              source: 'ground_truth+babelio'
            }
          })
        };
        BiblioValidationService.mockImplementation(() => mockService);

        wrapper = mount(BiblioValidationCell, {
          props: {
            author: 'Alain Mabancou',
            title: 'Ramsès de Paris',
            publisher: 'Seuil'
          }
        });

        await new Promise(resolve => setTimeout(resolve, 50));
        await wrapper.vm.$nextTick();

        // Should show 🔄 Suggestion
        expect(wrapper.find('[data-testid="validation-suggestion"]').exists()).toBe(true);
        expect(wrapper.text()).toContain('🔄');
        expect(wrapper.text()).toContain('Suggestion');
        expect(wrapper.text()).toContain('Alain Mabanckou'); // Corrected author
        expect(wrapper.text()).toContain('Ramsès de Paris');

        // Verify service was called correctly
        expect(mockService.validateBiblio).toHaveBeenCalledWith(
          'Alain Mabancou',
          'Ramsès de Paris',
          'Seuil',
          null
        );
      });

      it('should prioritize ground truth: Colcause -> Kolkhoze (Emmanuel Carrère)', async () => {
        // Given: Episode ground truth contains "Kolkhoze"
        const { BiblioValidationService } = await import('../../src/services/BiblioValidationService.js');

        const mockService = {
          validateBiblio: vi.fn().mockResolvedValue({
            status: 'suggestion',
            data: {
              original: {
                author: 'Emmanuel Carrère',
                title: 'Colcause',          // Typo
                publisher: 'POL'
              },
              suggested: {
                author: 'Emmanuel Carrère',
                title: 'Kolkhoze'           // Ground truth correction
              },
              corrections: {
                author: false,
                title: true
              },
              source: 'ground_truth+babelio'
            }
          })
        };
        BiblioValidationService.mockImplementation(() => mockService);

        wrapper = mount(BiblioValidationCell, {
          props: {
            author: 'Emmanuel Carrère',
            title: 'Colcause',
            publisher: 'POL',
            episodeId: '68bd9ed3582cf994fb66f1d6'  // pragma: allowlist secret
          }
        });

        await new Promise(resolve => setTimeout(resolve, 50));
        await wrapper.vm.$nextTick();

        // Should suggest Kolkhoze from ground truth, not Babelio's wrong suggestion
        expect(wrapper.find('[data-testid="validation-suggestion"]').exists()).toBe(true);
        expect(wrapper.text()).toContain('🔄');
        expect(wrapper.text()).toContain('Kolkhoze');
        expect(wrapper.text()).not.toContain('À quelques secondes près');
      });
    });

    describe('❓ Non trouvé (aucune correspondance fiable)', () => {
      it('should reject unreliable suggestions: Agnès Michaud - Huitsemences vivantes', async () => {
        // Given: Real data from /livres-auteurs that has no reliable match
        const { BiblioValidationService } = await import('../../src/services/BiblioValidationService.js');

        const mockService = {
          validateBiblio: vi.fn().mockResolvedValue({
            status: 'not_found',
            data: {
              original: {
                author: 'Agnès Michaud',
                title: 'Huitsemences vivantes',
                publisher: 'Éditeur'
              },
              reason: 'no_reliable_match_found',
              attempts: ['ground_truth', 'babelio']
            }
          })
        };
        BiblioValidationService.mockImplementation(() => mockService);

        wrapper = mount(BiblioValidationCell, {
          props: {
            author: 'Agnès Michaud',
            title: 'Huitsemences vivantes',
            publisher: 'Éditeur'
          }
        });

        await new Promise(resolve => setTimeout(resolve, 50));
        await wrapper.vm.$nextTick();

        // Should show ❓ Non trouvé (no unreliable suggestions)
        expect(wrapper.find('[data-testid="validation-not-found"]').exists()).toBe(true);
        expect(wrapper.text()).toContain('❓');
        expect(wrapper.text()).toContain('Non trouvé');
        expect(wrapper.text()).not.toContain('Suggestion');
        expect(wrapper.text()).not.toContain('Agnès Ouvrard-Michaud'); // No false suggestions

        // Verify service was called correctly
        expect(mockService.validateBiblio).toHaveBeenCalledWith(
          'Agnès Michaud',
          'Huitsemences vivantes',
          'Éditeur',
          null
        );
      });
    });

    describe('🔍 Real-world test cases', () => {
      it('should display Caroline du Saint suggestion for Caroline Dussain - Un déni français', async () => {
        // Given: BiblioValidationService returns the expected suggestion
        const { BiblioValidationService } = await import('../../src/services/BiblioValidationService.js');

        const mockService = {
          validateBiblio: vi.fn().mockResolvedValue({
            status: 'suggestion',
            data: {
              original: {
                author: 'Caroline Dussain',
                title: 'Un déni français',
                publisher: 'Éditeur'
              },
              suggested: {
                author: 'Caroline du Saint',
                title: "Un Déni français - Enquête sur l'élevage industrie..."
              },
              corrections: {
                author: true,
                title: true
              },
              source: 'babelio',
              confidence_score: 0.55
            }
          })
        };
        BiblioValidationService.mockImplementation(() => mockService);

        wrapper = mount(BiblioValidationCell, {
          props: {
            author: 'Caroline Dussain',
            title: 'Un déni français',
            publisher: 'Éditeur'
          }
        });

        await new Promise(resolve => setTimeout(resolve, 50));
        await wrapper.vm.$nextTick();

        // Then: Should display suggestion with correct author and title
        expect(wrapper.find('[data-testid="validation-suggestion"]').exists()).toBe(true);
        expect(wrapper.text()).toContain('🔄');
        expect(wrapper.text()).toContain('Suggestion');
        expect(wrapper.text()).toContain('Caroline du Saint');
        expect(wrapper.text()).toContain("Un Déni français - Enquête sur l'élevage industrie...");

        // Verify service was called with correct parameters
        expect(mockService.validateBiblio).toHaveBeenCalledWith(
          'Caroline Dussain',
          'Un déni français',
          'Éditeur',
          null
        );
      });

      it('should display Alain Mabanckou suggestion for Alain Mabancou - Ramsès de Paris', async () => {
        // Given: BiblioValidationService returns the expected suggestion
        const { BiblioValidationService } = await import('../../src/services/BiblioValidationService.js');

        const mockService = {
          validateBiblio: vi.fn().mockResolvedValue({
            status: 'suggestion',
            data: {
              original: {
                author: 'Alain Mabancou',
                title: 'Ramsès de Paris',
                publisher: 'Seuil'
              },
              suggested: {
                author: 'Alain Mabanckou',
                title: 'Ramsès de Paris' // Title unchanged
              },
              corrections: {
                author: true,
                title: false // No title correction
              },
              source: 'babelio',
              confidence_score: 0.96
            }
          })
        };
        BiblioValidationService.mockImplementation(() => mockService);

        wrapper = mount(BiblioValidationCell, {
          props: {
            author: 'Alain Mabancou',
            title: 'Ramsès de Paris',
            publisher: 'Seuil'
          }
        });

        await new Promise(resolve => setTimeout(resolve, 50));
        await wrapper.vm.$nextTick();

        // Then: Should display suggestion with corrected author only
        expect(wrapper.find('[data-testid="validation-suggestion"]').exists()).toBe(true);
        expect(wrapper.text()).toContain('🔄');
        expect(wrapper.text()).toContain('Suggestion');
        expect(wrapper.text()).toContain('Alain Mabanckou');
        expect(wrapper.text()).toContain('Ramsès de Paris');

        // Verify service was called with correct parameters
        expect(mockService.validateBiblio).toHaveBeenCalledWith(
          'Alain Mabancou',
          'Ramsès de Paris',
          'Seuil',
          null
        );
      });
    });
  });
});
