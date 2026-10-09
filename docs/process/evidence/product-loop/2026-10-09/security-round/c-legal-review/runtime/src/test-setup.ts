import '@testing-library/jest-dom/vitest';
import { afterAll } from 'vitest';
import guard from '../../network-deny.cjs';
afterAll(() => guard.flush('test-file'));
