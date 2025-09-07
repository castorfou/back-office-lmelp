/**
 * Tests unitaires pour le service API livresAuteursService
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock axios
const mockGet = vi.fn();
const mockCreate = vi.fn(() => ({
  get: mockGet,
  interceptors: {
    response: {
      use: vi.fn()
    }
  }
}));

vi.mock('axios', () => ({
  default: {
    create: mockCreate
  }
}));

import { livresAuteursService } from '../../src/services/api.js';

describe('livresAuteursService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getLivresAuteurs - récupère la liste des livres avec succès', async () => {
    const mockData = [
      {
        episode_oid: '6865f995a1418e3d7c63d076', // pragma: allowlist secret
        episode_title: 'Test Episode',
        episode_date: '01 jan. 2025',
        auteur: 'Test Auteur',
        titre: 'Test Livre',
        editeur: 'Test Éditeur',
        note_moyenne: 8.0,
        nb_critiques: 2,
        coups_de_coeur: ['Critique1', 'Critique2']
      }
    ];

    mockGet.mockResolvedValue({ data: mockData });

    const result = await livresAuteursService.getLivresAuteurs();

    expect(result).toEqual(mockData);
  });

  it('getLivresAuteurs - appelle le bon endpoint', async () => {
    mockGet.mockResolvedValue({ data: [] });

    await livresAuteursService.getLivresAuteurs();

    expect(mockGet).toHaveBeenCalledWith('/livres-auteurs', { params: {} });
  });

  it('getLivresAuteurs - passe les paramètres de requête', async () => {
    mockGet.mockResolvedValue({ data: [] });

    await livresAuteursService.getLivresAuteurs({ limit: 10 });

    expect(mockGet).toHaveBeenCalledWith('/livres-auteurs', { params: { limit: 10 } });
  });

  it('getLivresAuteurs - gère les réponses vides', async () => {
    mockGet.mockResolvedValue({ data: [] });

    const result = await livresAuteursService.getLivresAuteurs();

    expect(result).toEqual([]);
    expect(Array.isArray(result)).toBe(true);
  });
});
