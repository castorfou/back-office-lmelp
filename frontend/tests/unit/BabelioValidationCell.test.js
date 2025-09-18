/**
 * Tests pour le composant BabelioValidationCell
 * Affiche les statuts de validation Babelio avec indicateurs visuels
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import BabelioValidationCell from '../../src/components/BabelioValidationCell.vue';

// Mock the babelio service
vi.mock('../../src/services/api.js', () => ({
  babelioService: {
    verifyAuthor: vi.fn(),
    verifyBook: vi.fn(),
    verifyPublisher: vi.fn(),
  }
}));

describe('BabelioValidationCell', () => {
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
      const { babelioService } = await import('../../src/services/api.js');

      // Mock a slow response to test loading state
      babelioService.verifyAuthor.mockImplementation(() =>
        new Promise(resolve => setTimeout(() => resolve({
          status: 'verified',
          original: 'Michel Houellebecq',
          babelio_suggestion: 'Michel Houellebecq',
          confidence_score: 1.0
        }), 100))
      );

      wrapper = mount(BabelioValidationCell, {
        props: defaultProps
      });

      // Wait for component to mount and start validation
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-testid="validation-loading"]').exists()).toBe(true);
      expect(wrapper.text()).toContain('Vérification...');
    });

    it('should show validation starting automatically on mount', async () => {
      const { babelioService } = await import('../../src/services/api.js');

      babelioService.verifyAuthor.mockResolvedValue({
        status: 'verified',
        original: 'Michel Houellebecq',
        babelio_suggestion: 'Michel Houellebecq',
        confidence_score: 1.0
      });

      wrapper = mount(BabelioValidationCell, {
        props: defaultProps
      });

      // Wait for mounted lifecycle
      await wrapper.vm.$nextTick();

      // Should start validation on mount
      expect(babelioService.verifyAuthor).toHaveBeenCalledWith('Michel Houellebecq');
    });
  });

  describe('Success states', () => {
    it('should display perfect match indicator for verified author and book', async () => {
      const { babelioService } = await import('../../src/services/api.js');

      const mockAuthorResponse = {
        status: 'verified',
        original: 'Michel Houellebecq',
        babelio_suggestion: 'Michel Houellebecq',
        confidence_score: 1.0
      };

      const mockBookResponse = {
        status: 'verified',
        original_title: 'Les Particules élémentaires',
        babelio_suggestion_title: 'Les Particules élémentaires',
        confidence_score: 1.0
      };

      babelioService.verifyAuthor.mockResolvedValue(mockAuthorResponse);
      babelioService.verifyBook.mockResolvedValue(mockBookResponse);

      wrapper = mount(BabelioValidationCell, {
        props: defaultProps
      });

      // Wait for validation to complete (author + book validation)
      await new Promise(resolve => setTimeout(resolve, 1100)); // Account for rate limiting
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-testid="validation-success"]').exists()).toBe(true);
      expect(wrapper.text()).toContain('✅');
      expect(wrapper.text()).toContain('Validé');
    });

    it('should display suggestion for corrected author validated by book', async () => {
      const { babelioService } = await import('../../src/services/api.js');

      const mockAuthorResponse = {
        status: 'corrected',
        original: 'Michel Houellebeck',
        babelio_suggestion: 'Michel Houellebecq',
        confidence_score: 0.9
      };

      const mockBookResponse = {
        status: 'verified',
        original_title: 'Les Particules élémentaires',
        babelio_suggestion_title: 'Les Particules élémentaires',
        confidence_score: 1.0
      };

      babelioService.verifyAuthor.mockResolvedValue(mockAuthorResponse);
      babelioService.verifyBook.mockResolvedValue(mockBookResponse);

      wrapper = mount(BabelioValidationCell, {
        props: defaultProps
      });

      // Wait for validation to complete (author + book validation)
      await new Promise(resolve => setTimeout(resolve, 1100));
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-testid="validation-suggestion"]').exists()).toBe(true);
      expect(wrapper.text()).toContain('🔄');
      expect(wrapper.text()).toContain('Michel Houellebecq');
      expect(wrapper.text()).toContain('Suggestion');
    });

    it('should display not found indicator when no match exists', async () => {
      const { babelioService } = await import('../../src/services/api.js');

      const mockResponse = {
        status: 'not_found',
        original: 'Auteur Inexistant',
        babelio_suggestion: null,
        confidence_score: 0
      };

      babelioService.verifyAuthor.mockResolvedValue(mockResponse);

      wrapper = mount(BabelioValidationCell, {
        props: defaultProps
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
      const { babelioService } = await import('../../src/services/api.js');

      babelioService.verifyAuthor.mockRejectedValue(new Error('Network error'));

      wrapper = mount(BabelioValidationCell, {
        props: defaultProps
      });

      // Wait for validation to complete
      await new Promise(resolve => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-testid="validation-error"]').exists()).toBe(true);
      expect(wrapper.text()).toContain('⚠️');
      expect(wrapper.text()).toContain('Erreur');
    });

    it('should provide retry functionality on error', async () => {
      const { babelioService } = await import('../../src/services/api.js');

      babelioService.verifyAuthor.mockRejectedValue(new Error('Network error'));

      wrapper = mount(BabelioValidationCell, {
        props: defaultProps
      });

      // Wait for initial error
      await new Promise(resolve => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();

      const retryButton = wrapper.find('[data-testid="retry-button"]');
      expect(retryButton.exists()).toBe(true);

      // Mock successful retry
      babelioService.verifyAuthor.mockClear();
      babelioService.verifyAuthor.mockResolvedValue({
        status: 'verified',
        original: 'Michel Houellebecq',
        babelio_suggestion: 'Michel Houellebecq',
        confidence_score: 1.0
      });

      // Clear the lastValidationTime to avoid rate limiting during retry
      wrapper.vm.lastValidationTime = 0;

      await retryButton.trigger('click');

      // Wait longer for the retry validation to complete (considering rate limiting)
      await new Promise(resolve => setTimeout(resolve, 1200)); // 1.2 seconds to account for rate limiting
      await wrapper.vm.$nextTick();

      // Should now show success state
      expect(wrapper.find('[data-testid="validation-success"]').exists()).toBe(true);
    });
  });

  describe('Rate limiting', () => {
    it('should respect rate limiting by delaying verification', async () => {
      wrapper = mount(BabelioValidationCell, {
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

  describe('Book verification', () => {
    it('should verify book with author when both are provided', async () => {
      const { babelioService } = await import('../../src/services/api.js');

      babelioService.verifyBook.mockResolvedValue({
        status: 'verified',
        original_title: 'Les Particules élémentaires',
        original_author: 'Michel Houellebecq'
      });

      wrapper = mount(BabelioValidationCell, {
        props: defaultProps
      });

      await wrapper.vm.verifyBook();

      expect(babelioService.verifyBook).toHaveBeenCalledWith(
        'Les Particules élémentaires',
        'Michel Houellebecq'
      );
    });
  });

  describe('Invalid suggestion handling', () => {
    it('should display invalid suggestion when author suggestion not validated by book', async () => {
      const { babelioService } = await import('../../src/services/api.js');

      const mockAuthorResponse = {
        status: 'corrected',
        original: 'Agnès Michaud',
        babelio_suggestion: 'Agnès Ouvrard-Michaud',
        confidence_score: 0.8
      };

      const mockBookResponse = {
        status: 'not_found',
        original_title: 'Le Titre Inexistant'
      };

      babelioService.verifyAuthor.mockResolvedValue(mockAuthorResponse);
      babelioService.verifyBook.mockResolvedValue(mockBookResponse);

      wrapper = mount(BabelioValidationCell, {
        props: defaultProps
      });

      // Wait for validation to complete
      await new Promise(resolve => setTimeout(resolve, 1100));
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-testid="validation-invalid"]').exists()).toBe(true);
      expect(wrapper.text()).toContain('⚠️');
      expect(wrapper.text()).toContain('Suggestion invalide');
    });
  });

  describe('Props validation', () => {
    it('should handle missing author gracefully', () => {
      wrapper = mount(BabelioValidationCell, {
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
      const { babelioService } = await import('../../src/services/api.js');

      babelioService.verifyAuthor.mockResolvedValue({
        status: 'verified',
        original: 'Some Author',
        babelio_suggestion: 'Some Author',
        confidence_score: 1.0
      });

      wrapper = mount(BabelioValidationCell, {
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
});
