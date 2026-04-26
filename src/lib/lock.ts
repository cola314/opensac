export interface CrawlLock {
  // key에 대해 lock 획득 시도. 이미 진행 중이면 완료될 때까지 대기.
  // 반환: { acquired: true } 이면 크롤링 실행해야 함, { acquired: false } 이면 이미 다른 요청이 완료함
  acquire(key: string): Promise<{ acquired: boolean }>;
  release(key: string): void;
}

type Resolver = () => void;

class InMemoryLock implements CrawlLock {
  private locks = new Map<string, { promise: Promise<void>; resolve: Resolver }>();

  async acquire(key: string): Promise<{ acquired: boolean }> {
    const existing = this.locks.get(key);
    if (existing) {
      await existing.promise;
      return { acquired: false };
    }

    let resolve!: Resolver;
    const promise = new Promise<void>((res) => {
      resolve = res;
    });
    this.locks.set(key, { promise, resolve });
    return { acquired: true };
  }

  release(key: string): void {
    const entry = this.locks.get(key);
    if (entry) {
      this.locks.delete(key);
      entry.resolve();
    }
  }
}

let instance: InMemoryLock | null = null;

export function getInMemoryLock(): CrawlLock {
  if (!instance) {
    instance = new InMemoryLock();
  }
  return instance;
}
