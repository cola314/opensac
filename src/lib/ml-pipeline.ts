import { execFile } from 'child_process';
import { writeFile, readFile, unlink, mkdir } from 'fs/promises';
import { join } from 'path';
import { tmpdir } from 'os';
import { randomUUID } from 'crypto';

interface PipelineInput {
  sn: string;
  title: string;
  detail_text: string;
}

interface PipelineResult {
  sn: string;
  title: string;
  programs: Array<{ composer: string; piece: string }>;
  error?: string;
}

function getMlDir(): string {
  return process.env.ML_DIR || join(process.cwd(), 'ml');
}

function getCompiledProgram(): string {
  return process.env.ML_COMPILED_PROGRAM || join(getMlDir(), 'optimize', 'compiled_program.json');
}

export async function runPipeline(items: PipelineInput[]): Promise<PipelineResult[]> {
  const mlDir = getMlDir();
  const compiledProgram = getCompiledProgram();
  const tmpId = randomUUID().slice(0, 8);
  const tmpDir = join(tmpdir(), 'opensac-ml');
  await mkdir(tmpDir, { recursive: true });

  const inputPath = join(tmpDir, `input-${tmpId}.json`);
  const outputPath = join(tmpDir, `output-${tmpId}.json`);

  const inputData = items.map((item) => ({
    sn: item.sn,
    title: item.title,
    input: item.detail_text,
  }));

  await writeFile(inputPath, JSON.stringify(inputData, null, 2), 'utf-8');

  try {
    await new Promise<void>((resolve, reject) => {
      const pythonPath = process.env.ML_PYTHON || 'python3';
      const scriptPath = join(mlDir, 'parser', 'pipeline.py');

      execFile(
        pythonPath,
        [
          scriptPath,
          '--input', inputPath,
          '--output', outputPath,
          '--compiled-program', compiledProgram,
        ],
        {
          cwd: mlDir,
          env: {
            ...process.env,
            PYTHONPATH: mlDir,
          },
          timeout: 300_000, // 5 minutes
        },
        (error, _stdout, stderr) => {
          if (error) {
            console.error('Pipeline stderr:', stderr);
            reject(new Error(`Pipeline failed: ${error.message}`));
          } else {
            resolve();
          }
        }
      );
    });

    const outputRaw = await readFile(outputPath, 'utf-8');
    const results: PipelineResult[] = JSON.parse(outputRaw);
    return results;
  } finally {
    await unlink(inputPath).catch(() => {});
    await unlink(outputPath).catch(() => {});
  }
}
