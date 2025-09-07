/**
 * Tests unitaires pour le service API livresAuteursService
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock des modules avant les imports
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(),
      put: vi.fn(),
      interceptors: {
        response: {
          use: vi.fn()
        }
      }
    }))
  }
}));

import axios from 'axios';
import { livresAuteursService } from '../../src/services/api.js';

const mockedAxios = vi.mocked(axios);

describe('livresAuteursService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
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

    mockedAxios.create.mockReturnValue({
      get: vi.fn().mockResolvedValue({ data: mockData }),
      interceptors: {
        response: {
          use: vi.fn()
        }
      }
    });

    const result = await livresAuteursService.getLivresAuteurs();

    expect(result).toEqual(mockData);
  });

  it('getLivresAuteurs - gère les erreurs réseau', async () => {
    const mockError = new Error('Network Error');
    mockError.request = true;

    mockedAxios.create.mockReturnValue({
      get: vi.fn().mockRejectedValue(mockError),
      interceptors: {
        response: {
          use: vi.fn()
        }
      }
    });

    await expect(livresAuteursService.getLivresAuteurs()).rejects.toThrow('Erreur réseau: Impossible de contacter le serveur');
  });

  it('getLivresAuteurs - gère les erreurs serveur avec détail', async () => {
    const mockError = new Error('Server Error');
    mockError.response = {
      data: {
        detail: 'Erreur de traitement LLM'
      }
    };

    mockedAxios.create.mockReturnValue({
      get: vi.fn().mockRejectedValue(mockError),
      interceptors: {
        response: {
          use: vi.fn()
        }
      }
    });

    await expect(livresAuteursService.getLivresAuteurs()).rejects.toThrow('Erreur de traitement LLM');
  });

  it('getLivresAuteurs - gère les timeouts', async () => {
    const mockError = new Error('Timeout');
    mockError.code = 'ECONNABORTED';

    mockedAxios.create.mockReturnValue({
      get: vi.fn().mockRejectedValue(mockError),
      interceptors: {
        response: {
          use: vi.fn()
        }
      }
    });

    await expect(livresAuteursService.getLivresAuteurs()).rejects.toThrow('Timeout: La requête a pris trop de temps');
  });

  it('getLivresAuteurs - appelle le bon endpoint', async () => {
    const mockAxiosInstance = {
      get: vi.fn().mockResolvedValue({ data: [] }),
      interceptors: {
        response: {
          use: vi.fn()
        }
      }
    };

    mockedAxios.create.mockReturnValue(mockAxiosInstance);

    await livresAuteursService.getLivresAuteurs();

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/livres-auteurs');
  });

  it('getLivresAuteurs - passe les paramètres de requête', async () => {
    const mockAxiosInstance = {
      get: vi.fn().mockResolvedValue({ data: [] }),
      interceptors: {
        response: {
          use: vi.fn()
        }
      }
    };

    mockedAxios.create.mockReturnValue(mockAxiosInstance);

    await livresAuteursService.getLivresAuteurs({ limit: 10 });

    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/livres-auteurs', { params: { limit: 10 } });
  });

  it('getLivresAuteurs - valide le format des données retournées', async () => {
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
        coups_de_coeur: ['Critique1']
      }
    ];

    mockedAxios.create.mockReturnValue({
      get: vi.fn().mockResolvedValue({ data: mockData }),
      interceptors: {
        response: {
          use: vi.fn()
        }
      }
    });

    const result = await livresAuteursService.getLivresAuteurs();

    expect(Array.isArray(result)).toBe(true);
    expect(result).toHaveLength(1);

    const book = result[0];
    expect(typeof book.episode_oid).toBe('string');
    expect(typeof book.episode_title).toBe('string');
    expect(typeof book.episode_date).toBe('string');
    expect(typeof book.auteur).toBe('string');
    expect(typeof book.titre).toBe('string');
    expect(typeof book.editeur).toBe('string');
    expect(typeof book.note_moyenne).toBe('number');
    expect(typeof book.nb_critiques).toBe('number');
    expect(Array.isArray(book.coups_de_coeur)).toBe(true);
  });

  it('getLivresAuteurs - gère les réponses vides', async () => {
    mockedAxios.create.mockReturnValue({
      get: vi.fn().mockResolvedValue({ data: [] }),
      interceptors: {
        response: {
          use: vi.fn()
        }
      }
    });

    const result = await livresAuteursService.getLivresAuteurs();

    expect(result).toEqual([]);
    expect(Array.isArray(result)).toBe(true);
  });

  it('getLivresAuteurs - utilise la configuration axios par défaut', async () => {
    mockedAxios.create.mockReturnValue({
      get: vi.fn().mockResolvedValue({ data: [] }),
      interceptors: {
        response: {
          use: vi.fn()
        }
      }
    });

    await livresAuteursService.getLivresAuteurs();

    expect(mockedAxios.create).toHaveBeenCalledWith({
      baseURL: '/api',
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  });

  it('getLivresAuteurs - préserve les métadonnées d\'épisode', async () => {
    const mockData = [
      {
        episode_oid: '6865f995a1418e3d7c63d076', // pragma: allowlist secret
        episode_title: 'Episode complet avec métadonnées',
        episode_date: '01 jan. 2025',
        auteur: 'Test Auteur',
        titre: 'Test Livre',
        editeur: 'Test Éditeur',
        note_moyenne: 8.0,
        nb_critiques: 2,
        coups_de_coeur: []
      }
    ];

    mockedAxios.create.mockReturnValue({
      get: vi.fn().mockResolvedValue({ data: mockData }),
      interceptors: {
        response: {
          use: vi.fn()
        }
      }
    });

    const result = await livresAuteursService.getLivresAuteurs();

    const book = result[0];
    expect(book.episode_oid).toBe('6865f995a1418e3d7c63d076'); // pragma: allowlist secret
    expect(book.episode_title).toBe('Episode complet avec métadonnées');
    expect(book.episode_date).toBe('01 jan. 2025');
  });
});
