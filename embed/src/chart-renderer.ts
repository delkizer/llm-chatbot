/**
 * SPO Chatbot - Chart Renderer (Chart.js Wrapper)
 */

import { Chart, registerables } from 'chart.js';
import type { ChartData } from './types';

Chart.register(...registerables);

export class ChartRenderer {
  private charts: Map<string, Chart> = new Map();
  private chartCounter = 0;

  render(container: HTMLElement, chartData: ChartData): HTMLElement {
    const wrapper = document.createElement('div');
    wrapper.className = 'spo-chart';

    // 제목
    const title = document.createElement('div');
    title.className = 'spo-chart-title';
    title.textContent = chartData.title;
    wrapper.appendChild(title);

    // 캔버스
    const canvas = document.createElement('canvas');
    const chartId = `spo-chart-${++this.chartCounter}`;
    canvas.id = chartId;
    wrapper.appendChild(canvas);

    container.appendChild(wrapper);

    // Chart.js 인스턴스 생성
    const colors = this.getThemeColors(container);
    const chart = new Chart(canvas, {
      type: chartData.type,
      data: {
        labels: chartData.data.labels,
        datasets: chartData.data.datasets.map((ds, i) => ({
          label: ds.label,
          data: ds.data,
          backgroundColor: this.getBackgroundColors(chartData.type, colors, i, chartData.data.labels.length),
          borderColor: colors[i % colors.length],
          borderWidth: chartData.type === 'pie' ? 1 : 2,
          fill: false,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            display: chartData.data.datasets.length > 1 || chartData.type === 'pie',
            position: 'bottom',
            labels: { font: { size: 11 } },
          },
        },
        scales: chartData.type === 'pie' ? {} : {
          y: { beginAtZero: true },
        },
      },
    });

    this.charts.set(chartId, chart);
    return wrapper;
  }

  destroy(chartId: string): void {
    const chart = this.charts.get(chartId);
    if (chart) {
      chart.destroy();
      this.charts.delete(chartId);
    }
  }

  destroyAll(): void {
    this.charts.forEach(chart => chart.destroy());
    this.charts.clear();
  }

  private getThemeColors(container: HTMLElement): string[] {
    const style = getComputedStyle(container);
    const colors: string[] = [];
    for (let i = 1; i <= 5; i++) {
      const color = style.getPropertyValue(`--spo-chart-color-${i}`).trim();
      if (color) colors.push(color);
    }
    return colors.length > 0 ? colors : ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6'];
  }

  private getBackgroundColors(
    type: string,
    colors: string[],
    datasetIndex: number,
    labelCount: number
  ): string | string[] {
    if (type === 'pie') {
      return Array.from({ length: labelCount }, (_, i) => colors[i % colors.length]);
    }
    return colors[datasetIndex % colors.length];
  }
}
