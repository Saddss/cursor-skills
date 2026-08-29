# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "cairosvg>=2.7.1",
#   "fonttools>=4.59.0",
#   "pillow>=10.4.0",
#   "pyppeteer>=2.0.0",
# ]
# ///
"""Render and validate academic SVG figures at their final physical size."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any

import cairosvg
from PIL import Image, ImageStat
from pyppeteer import launch

from font_glyph_audit import audit_svg_fonts


MM_TO_CSS_PX = 96 / 25.4
PREVIEW_DPI = 600


def svg_width_mm(svg_text: str) -> float:
    match = re.search(r'<svg\b[^>]*\bwidth=["\']\s*([0-9.]+)\s*(mm|cm|in|pt|px)?["\']', svg_text)
    if not match:
        raise ValueError("SVG root is missing a numeric width")
    value = float(match.group(1))
    unit = match.group(2) or "px"
    factors = {"mm": 1.0, "cm": 10.0, "in": 25.4, "pt": 25.4 / 72.0, "px": 25.4 / 96.0}
    return value * factors[unit]


def _chromium_path() -> str | None:
    configured = os.environ.get("PYPPETEER_EXECUTABLE_PATH")
    if configured and Path(configured).exists():
        return configured
    cached = sorted(
        (Path.home() / ".local/share/pyppeteer/local-chromium").glob("*/chrome-linux/chrome"),
        reverse=True,
    )
    candidates = [*cached, Path("/usr/bin/chromium"), Path("/usr/bin/google-chrome")]
    return str(next((path for path in candidates if path.exists()), "")) or None


async def inspect_svg(page: Any, svg_path: Path) -> dict[str, Any]:
    await page.goto(svg_path.resolve().as_uri(), {"waitUntil": "load"})
    await page.evaluate("document.fonts.ready")
    return await page.evaluate(
        """() => {
          const svg = document.querySelector('svg');
          const root = svg.getBoundingClientRect();
          const mm = 96 / 25.4;
          const textMargin = 1.0 * mm;
          const canvasMargin = 1.5 * mm;

          const rectOf = (el) => {
            const r = el.getBoundingClientRect();
            return {left:r.left, right:r.right, top:r.top, bottom:r.bottom,
                    width:r.width, height:r.height};
          };
          const labelOf = (el) => (el.textContent || '').replace(/\\s+/g, ' ').trim();
          const texts = [...svg.querySelectorAll('text')].filter(el => {
            const r = el.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
          });
          const textRects = texts.map((el, i) => ({i, el, label:labelOf(el), rect:rectOf(el)}));
          const issues = [];
          const semanticMetrics = [];

          const requiredFonts = ['Noto Sans CJK SC', 'Liberation Sans'];
          for (const family of requiredFonts) {
            if (!document.fonts.check(`19px "${family}"`)) {
              issues.push({type:'required-font-unavailable', family});
            }
          }

          for (const item of textRects) {
            if ((item.el.textContent || '').includes('\u3000')) {
              issues.push({type:'ideographic-space-layout', label:item.label});
            }
            const style = getComputedStyle(item.el);
            const classes = item.el.classList;
            const size = Number.parseFloat(style.fontSize);
            const weight = style.fontWeight;
            if (size < 19) {
              issues.push({type:'font-size-below-floor', label:item.label, sizePx:size, minimumPx:19});
            }
            if (!['400', '700'].includes(weight)) {
              issues.push({type:'synthetic-font-weight', label:item.label, weight});
            }
            if (style.textShadow !== 'none' || (style.stroke !== 'none' && style.stroke !== 'rgba(0, 0, 0, 0)')) {
              issues.push({type:'text-effect-forbidden', label:item.label,
                           textShadow:style.textShadow, stroke:style.stroke});
            }
            if (classes.contains('math') || classes.contains('mathb')) {
              if (!style.fontFamily.includes('Liberation Sans')) {
                issues.push({type:'font-role-mismatch', label:item.label,
                             role:'math', fontFamily:style.fontFamily});
              }
            } else if (classes.contains('t')) {
              if (!style.fontFamily.includes('Noto Sans CJK SC')) {
                issues.push({type:'font-role-mismatch', label:item.label,
                             role:'label', fontFamily:style.fontFamily});
              }
            } else {
              issues.push({type:'missing-font-role', label:item.label,
                           classes:[...classes]});
            }
          }

          for (const text of texts) {
            if (text.getAttribute('text-anchor') !== 'middle') continue;
            const implicitSegments = [...text.children].filter(child =>
              child.tagName.toLowerCase() === 'tspan' &&
              !child.hasAttribute('x') &&
              !child.hasAttribute('y')
            );
            const segmentFamilies = new Set(implicitSegments.map(child => getComputedStyle(child).fontFamily));
            if (implicitSegments.length > 1 && segmentFamilies.size > 1) {
              issues.push({type:'centered-mixed-font-tspan', label:labelOf(text),
                           families:[...segmentFamilies]});
            }
          }

          const typographyGroups = new Map();
          for (const item of svg.querySelectorAll('text[data-typography-group]')) {
            const id = item.getAttribute('data-typography-group');
            if (!typographyGroups.has(id)) typographyGroups.set(id, []);
            typographyGroups.get(id).push(item);
          }
          for (const [id, items] of typographyGroups) {
            if (items.length < 2) continue;
            const styles = items.map(item => getComputedStyle(item));
            const sizes = styles.map(style => Number.parseFloat(style.fontSize));
            const weights = [...new Set(styles.map(style => style.fontWeight))];
            const families = [...new Set(styles.map(style => style.fontFamily))];
            const sizeSpreadPx = Math.max(...sizes) - Math.min(...sizes);
            semanticMetrics.push({typographyGroup:id,
                                  itemCount:items.length,
                                  sizeSpreadPx:Number(sizeSpreadPx.toFixed(2)),
                                  sizesPx:[...new Set(sizes)].sort((a,b)=>a-b),
                                  weights,
                                  families});
            if (sizeSpreadPx > 0.1 || weights.length > 1 || families.length > 1) {
              issues.push({type:'typography-group-mismatch', group:id,
                           labels:items.map(labelOf),
                           sizesPx:[...new Set(sizes)].sort((a,b)=>a-b),
                           weights, families});
            }
          }

          const semanticArrowKeys = new Set(
            [...svg.querySelectorAll('[data-legend-key]')]
              .map(item => item.getAttribute('data-legend-key'))
              .filter(Boolean)
          );
          const legendKeys = new Set(
            [...svg.querySelectorAll('[data-legend-for]')]
              .map(item => item.getAttribute('data-legend-for'))
              .filter(Boolean)
          );
          if (semanticArrowKeys.size || legendKeys.size) {
            const missing = [...semanticArrowKeys].filter(key => !legendKeys.has(key)).sort();
            const orphan = [...legendKeys].filter(key => !semanticArrowKeys.has(key)).sort();
            semanticMetrics.push({legendCoverage:true,
                                  semanticKeys:[...semanticArrowKeys].sort(),
                                  legendKeys:[...legendKeys].sort(),
                                  missing, orphan});
            if (missing.length || orphan.length) {
              issues.push({type:'arrow-legend-coverage-mismatch', missing, orphan});
            }
          }

          for (const item of textRects) {
            const r = item.rect;
            if (r.left < root.left + canvasMargin || r.right > root.right - canvasMargin ||
                r.top < root.top + canvasMargin || r.bottom > root.bottom - canvasMargin) {
              issues.push({type:'canvas-overflow', label:item.label, rect:r});
            }
            if (!(item.el.getComputedTextLength() > 0)) {
              issues.push({type:'empty-text-metrics', label:item.label});
            }
          }

          for (let i = 0; i < textRects.length; i++) {
            for (let j = i + 1; j < textRects.length; j++) {
              const a = textRects[i], b = textRects[j];
              const separated =
                a.rect.right + textMargin <= b.rect.left ||
                b.rect.right + textMargin <= a.rect.left ||
                a.rect.bottom + textMargin <= b.rect.top ||
                b.rect.bottom + textMargin <= a.rect.top;
              if (!separated) {
                issues.push({type:'text-text', a:a.label, b:b.label,
                             aRect:a.rect, bRect:b.rect});
              }
            }
          }

          const boundaryRects = [...svg.querySelectorAll('[data-boundary-obstacle="true"]')];
          for (const boundary of boundaryRects) {
            const br = boundary.getBoundingClientRect();
            for (const item of textRects) {
              const tr = item.rect;
              const safelyInside =
                tr.left >= br.left + textMargin && tr.right <= br.right - textMargin &&
                tr.top >= br.top + textMargin && tr.bottom <= br.bottom - textMargin;
              const safelyOutside =
                tr.right + textMargin <= br.left || br.right + textMargin <= tr.left ||
                tr.bottom + textMargin <= br.top || br.bottom + textMargin <= tr.top;
              if (!safelyInside && !safelyOutside) {
                issues.push({type:'text-boundary-collision', label:item.label,
                             boundary:rectOf(boundary)});
              }
            }
          }

          const obstacles = [...svg.querySelectorAll('[data-obstacle="true"]')];
          for (const obstacle of obstacles) {
            const length = obstacle.getTotalLength ? obstacle.getTotalLength() : 0;
            if (!(length > 0)) continue;
            const samples = Math.max(80, Math.ceil(length / 2));
            const matrix = obstacle.getScreenCTM();
            for (const item of textRects) {
              const r = item.rect;
              const expanded = {left:r.left-textMargin, right:r.right+textMargin,
                                top:r.top-textMargin, bottom:r.bottom+textMargin};
              let hit = false;
              for (let k = 0; k <= samples; k++) {
                const p = obstacle.getPointAtLength(length * k / samples);
                const q = new DOMPoint(p.x, p.y).matrixTransform(matrix);
                if (q.x >= expanded.left && q.x <= expanded.right &&
                    q.y >= expanded.top && q.y <= expanded.bottom) {
                  hit = true;
                  break;
                }
              }
              if (hit) {
                issues.push({type:'text-obstacle', label:item.label,
                             obstacle:obstacle.tagName + ':' + (obstacle.getAttribute('d') || '')});
              }
            }
          }

          const anchorMap = new Map();
          for (const anchor of svg.querySelectorAll('[data-anchor-id]')) {
            const id = anchor.getAttribute('data-anchor-id');
            if (anchorMap.has(id)) {
              issues.push({type:'duplicate-anchor-id', id});
            }
            anchorMap.set(id, anchor);
          }
          const allowedArrowRoles = new Set(['annotation', 'axis', 'self-loop']);
          const arrows = [...svg.querySelectorAll('[marker-end]')];
          const pointOnScreen = (el, atEnd) => {
            const length = el.getTotalLength();
            const point = el.getPointAtLength(atEnd ? length : 0);
            return new DOMPoint(point.x, point.y).matrixTransform(el.getScreenCTM());
          };
          const distancePointToRect = (point, rect) => {
            const dx = Math.max(rect.left - point.x, 0, point.x - rect.right);
            const dy = Math.max(rect.top - point.y, 0, point.y - rect.bottom);
            return Math.hypot(dx, dy);
          };
          for (const arrow of arrows) {
            const targetId = arrow.getAttribute('data-target-id');
            const role = arrow.getAttribute('data-arrow-role');
            const labelId = arrow.getAttribute('data-label-id');
            if (labelId) {
              const label = svg.querySelector(`[data-arrow-label-id="${CSS.escape(labelId)}"]`);
              if (!label) {
                issues.push({type:'arrow-label-missing', labelId});
              } else {
                const labelRect = label.getBoundingClientRect();
                const length = arrow.getTotalLength();
                const matrix = arrow.getScreenCTM();
                let distancePx = Infinity;
                for (let i = 0; i <= 80; i += 1) {
                  const p = arrow.getPointAtLength(length * i / 80);
                  const q = new DOMPoint(p.x, p.y).matrixTransform(matrix);
                  distancePx = Math.min(distancePx, distancePointToRect(q, labelRect));
                }
                const distanceMm = distancePx / mm;
                semanticMetrics.push({arrowLabel:labelId,
                                      distanceMm:Number(distanceMm.toFixed(2))});
                if (distanceMm < 1.0 || distanceMm > 4.0) {
                  issues.push({type:'arrow-label-distance', labelId,
                               distanceMm:Number(distanceMm.toFixed(2)), allowedMm:[1.0, 4.0]});
                }
              }
            }
            if (arrow.getAttribute('data-route') === 'orthogonal') {
              const elbowX = Number(arrow.getAttribute('data-elbow-x'));
              const elbowY = Number(arrow.getAttribute('data-elbow-y'));
              if (!Number.isFinite(elbowX) || !Number.isFinite(elbowY)) {
                issues.push({type:'orthogonal-elbow-missing'});
              } else {
                const matrix = svg.getScreenCTM();
                const elbow = new DOMPoint(elbowX, elbowY).matrixTransform(matrix);
                const start = pointOnScreen(arrow, false);
                const end = pointOnScreen(arrow, true);
                const firstLegDeviationMm = Math.abs(start.x - elbow.x) / mm;
                const secondLegDeviationMm = Math.abs(end.y - elbow.y) / mm;
                const firstLegLengthMm = Math.abs(elbow.y - start.y) / mm;
                const secondLegLengthMm = Math.abs(end.x - elbow.x) / mm;
                semanticMetrics.push({orthogonalRoute:true,
                                      firstLegDeviationMm:Number(firstLegDeviationMm.toFixed(2)),
                                      secondLegDeviationMm:Number(secondLegDeviationMm.toFixed(2)),
                                      firstLegLengthMm:Number(firstLegLengthMm.toFixed(2)),
                                      secondLegLengthMm:Number(secondLegLengthMm.toFixed(2))});
                if (firstLegDeviationMm > 0.2 || secondLegDeviationMm > 0.2) {
                  issues.push({type:'orthogonal-route-off-axis',
                               firstLegDeviationMm:Number(firstLegDeviationMm.toFixed(2)),
                               secondLegDeviationMm:Number(secondLegDeviationMm.toFixed(2)),
                               maximumMm:0.2});
                }
                if (firstLegLengthMm < 2.0 || secondLegLengthMm < 2.0) {
                  issues.push({type:'orthogonal-route-leg-too-short',
                               firstLegLengthMm:Number(firstLegLengthMm.toFixed(2)),
                               secondLegLengthMm:Number(secondLegLengthMm.toFixed(2)),
                               minimumMm:2.0});
                }
              }
            }
            if (arrow.getAttribute('data-route') === 'axis-aligned') {
              const start = pointOnScreen(arrow, false);
              const end = pointOnScreen(arrow, true);
              const axisDeviationMm = Math.min(Math.abs(start.y-end.y), Math.abs(start.x-end.x)) / mm;
              const routeLengthMm = Math.hypot(end.x-start.x, end.y-start.y) / mm;
              semanticMetrics.push({axisAlignedRoute:true,
                                    axisDeviationMm:Number(axisDeviationMm.toFixed(2)),
                                    routeLengthMm:Number(routeLengthMm.toFixed(2))});
              if (axisDeviationMm > 0.2) {
                issues.push({type:'axis-aligned-route-off-axis',
                             axisDeviationMm:Number(axisDeviationMm.toFixed(2)), maximumMm:0.2});
              }
              if (routeLengthMm < 4.0) {
                issues.push({type:'axis-aligned-route-too-short',
                             routeLengthMm:Number(routeLengthMm.toFixed(2)), minimumMm:4.0});
              }
            }
            if (arrow.getAttribute('data-route') === 'radial-diagonal') {
              const centerX = Number(arrow.getAttribute('data-center-x'));
              const centerY = Number(arrow.getAttribute('data-center-y'));
              if (!Number.isFinite(centerX) || !Number.isFinite(centerY)) {
                issues.push({type:'radial-center-missing'});
              } else {
                const matrix = svg.getScreenCTM();
                const center = new DOMPoint(centerX, centerY).matrixTransform(matrix);
                const start = pointOnScreen(arrow, false);
                const end = pointOnScreen(arrow, true);
                const dx = end.x - start.x;
                const dy = end.y - start.y;
                const lengthPx = Math.hypot(dx, dy);
                const radialDeviationPx = Math.abs(dy*center.x - dx*center.y + end.x*start.y - end.y*start.x) / lengthPx;
                const horizontalSpanMm = Math.abs(dx) / mm;
                const verticalSpanMm = Math.abs(dy) / mm;
                const radialDeviationMm = radialDeviationPx / mm;
                semanticMetrics.push({radialDiagonalRoute:true,
                                      radialDeviationMm:Number(radialDeviationMm.toFixed(2)),
                                      horizontalSpanMm:Number(horizontalSpanMm.toFixed(2)),
                                      verticalSpanMm:Number(verticalSpanMm.toFixed(2))});
                if (radialDeviationMm > 0.2) {
                  issues.push({type:'radial-route-off-center',
                               radialDeviationMm:Number(radialDeviationMm.toFixed(2)), maximumMm:0.2});
                }
                if (horizontalSpanMm < 4.0 || verticalSpanMm < 2.0) {
                  issues.push({type:'radial-route-not-diagonal',
                               horizontalSpanMm:Number(horizontalSpanMm.toFixed(2)),
                               verticalSpanMm:Number(verticalSpanMm.toFixed(2)),
                               minimumMm:[4.0, 2.0]});
                }
              }
            }
            if (!targetId) {
              if (!allowedArrowRoles.has(role)) {
                issues.push({type:'arrow-contract-missing',
                             arrow:arrow.getAttribute('d') || arrow.outerHTML.slice(0, 100)});
              }
              continue;
            }
            const target = anchorMap.get(targetId);
            const side = arrow.getAttribute('data-target-side');
            if (!target) {
              issues.push({type:'arrow-target-missing', targetId});
              continue;
            }
            if (!['left', 'right', 'top', 'bottom'].includes(side)) {
              issues.push({type:'arrow-target-side-missing', targetId, side});
              continue;
            }
            const end = pointOnScreen(arrow, true);
            const tr = target.getBoundingClientRect();
            let alignmentPx;
            let gapPx;
            if (side === 'left') {
              alignmentPx = Math.abs(end.y - (tr.top + tr.bottom) / 2);
              gapPx = tr.left - end.x;
            } else if (side === 'right') {
              alignmentPx = Math.abs(end.y - (tr.top + tr.bottom) / 2);
              gapPx = end.x - tr.right;
            } else if (side === 'top') {
              alignmentPx = Math.abs(end.x - (tr.left + tr.right) / 2);
              gapPx = tr.top - end.y;
            } else {
              alignmentPx = Math.abs(end.x - (tr.left + tr.right) / 2);
              gapPx = end.y - tr.bottom;
            }
            const alignmentMm = alignmentPx / mm;
            const gapMm = gapPx / mm;
            semanticMetrics.push({arrowTarget:targetId, side,
                                  alignmentErrorMm:Number(alignmentMm.toFixed(2)),
                                  terminalGapMm:Number(gapMm.toFixed(2))});
            if (alignmentMm > 0.5) {
              issues.push({type:'arrow-target-off-center', targetId, side,
                           alignmentErrorMm:Number(alignmentMm.toFixed(2)), maximumMm:0.5});
            }
            if (gapMm < 0.8 || gapMm > 2.0) {
              issues.push({type:'arrow-terminal-gap', targetId, side,
                           gapMm:Number(gapMm.toFixed(2)), allowedMm:[0.8, 2.0]});
            }

            const sourceId = arrow.getAttribute('data-source-id');
            if (sourceId) {
              const source = anchorMap.get(sourceId);
              const sourceSide = arrow.getAttribute('data-source-side');
              if (!source) {
                issues.push({type:'arrow-source-missing', sourceId});
              } else if (!['left', 'right', 'top', 'bottom', 'point'].includes(sourceSide)) {
                issues.push({type:'arrow-source-side-missing', sourceId, side:sourceSide});
              } else {
                const start = pointOnScreen(arrow, false);
                const sr = source.getBoundingClientRect();
                let sourceAlignmentPx;
                let sourceGapPx;
                if (sourceSide === 'point') {
                  const sourceX = Number(arrow.getAttribute('data-source-x'));
                  const sourceY = Number(arrow.getAttribute('data-source-y'));
                  if (!Number.isFinite(sourceX) || !Number.isFinite(sourceY)) {
                    issues.push({type:'arrow-source-point-missing', sourceId});
                    sourceAlignmentPx = Infinity;
                    sourceGapPx = Infinity;
                  } else {
                    const expected = new DOMPoint(sourceX, sourceY).matrixTransform(svg.getScreenCTM());
                    sourceAlignmentPx = Math.hypot(start.x-expected.x, start.y-expected.y);
                    const boundaryX = Number(arrow.getAttribute('data-source-boundary-x'));
                    const boundaryY = Number(arrow.getAttribute('data-source-boundary-y'));
                    if (Number.isFinite(boundaryX) && Number.isFinite(boundaryY)) {
                      const boundary = new DOMPoint(boundaryX, boundaryY).matrixTransform(svg.getScreenCTM());
                      sourceGapPx = Math.hypot(start.x-boundary.x, start.y-boundary.y);
                    } else {
                      sourceGapPx = 0;
                    }
                  }
                } else if (sourceSide === 'left') {
                  sourceAlignmentPx = Math.abs(start.y - (sr.top + sr.bottom) / 2);
                  sourceGapPx = sr.left - start.x;
                } else if (sourceSide === 'right') {
                  sourceAlignmentPx = Math.abs(start.y - (sr.top + sr.bottom) / 2);
                  sourceGapPx = start.x - sr.right;
                } else if (sourceSide === 'top') {
                  sourceAlignmentPx = Math.abs(start.x - (sr.left + sr.right) / 2);
                  sourceGapPx = sr.top - start.y;
                } else {
                  sourceAlignmentPx = Math.abs(start.x - (sr.left + sr.right) / 2);
                  sourceGapPx = start.y - sr.bottom;
                }
                const sourceAlignmentMm = sourceAlignmentPx / mm;
                const sourceGapMm = sourceGapPx / mm;
                const attachment = arrow.getAttribute('data-source-attachment') || 'gap';
                semanticMetrics.push({arrowSource:sourceId, side:sourceSide,
                                      attachment,
                                      alignmentErrorMm:Number(sourceAlignmentMm.toFixed(2)),
                                      terminalGapMm:Number(sourceGapMm.toFixed(2))});
                if (sourceAlignmentMm > 0.5) {
                  issues.push({type:'arrow-source-off-center', sourceId, side:sourceSide,
                               alignmentErrorMm:Number(sourceAlignmentMm.toFixed(2)), maximumMm:0.5});
                }
                const allowedSourceGap = attachment === 'touch' ? [-0.2, 0.2] : [0.8, 2.0];
                if (sourceGapMm < allowedSourceGap[0] || sourceGapMm > allowedSourceGap[1]) {
                  issues.push({type:'arrow-source-gap', sourceId, side:sourceSide,
                               attachment,
                               gapMm:Number(sourceGapMm.toFixed(2)), allowedMm:allowedSourceGap});
                }
              }
            }
          }

          const arrowStyleGroups = new Map();
          for (const arrow of svg.querySelectorAll('[data-arrow-style-group]')) {
            const id = arrow.getAttribute('data-arrow-style-group');
            if (!arrowStyleGroups.has(id)) arrowStyleGroups.set(id, []);
            arrowStyleGroups.get(id).push(arrow);
          }
          for (const [id, items] of arrowStyleGroups) {
            if (items.length < 2) continue;
            const widths = items.map(item => Number.parseFloat(getComputedStyle(item).strokeWidth));
            const markerSizes = items.map(item => {
              const match = (item.getAttribute('marker-end') || '').match(/#([^)'\"]+)/);
              const marker = match ? svg.querySelector(`#${CSS.escape(match[1])}`) : null;
              return marker ? [Number(marker.getAttribute('markerWidth')), Number(marker.getAttribute('markerHeight'))] : [NaN, NaN];
            });
            const angles = items.map(item => {
              const start = pointOnScreen(item, false);
              const end = pointOnScreen(item, true);
              let angle = Math.atan2(end.y-start.y, end.x-start.x);
              if (angle < 0) angle += Math.PI;
              if (angle >= Math.PI) angle -= Math.PI;
              return angle;
            });
            const lengthsPx = items.map(item => {
              const start = pointOnScreen(item, false);
              const end = pointOnScreen(item, true);
              return Math.hypot(end.x-start.x, end.y-start.y);
            });
            let maxParallelErrorRad = 0;
            for (let i = 1; i < angles.length; i += 1) {
              const raw = Math.abs(angles[i]-angles[0]);
              maxParallelErrorRad = Math.max(maxParallelErrorRad, Math.min(raw, Math.PI-raw));
            }
            const widthSpreadPx = Math.max(...widths)-Math.min(...widths);
            const markerWidthSpread = Math.max(...markerSizes.map(size => size[0]))-Math.min(...markerSizes.map(size => size[0]));
            const markerHeightSpread = Math.max(...markerSizes.map(size => size[1]))-Math.min(...markerSizes.map(size => size[1]));
            const parallelErrorDeg = maxParallelErrorRad * 180 / Math.PI;
            const lengthSpreadMm = (Math.max(...lengthsPx)-Math.min(...lengthsPx)) / mm;
            semanticMetrics.push({arrowStyleGroup:id,
                                  strokeWidthSpreadPx:Number(widthSpreadPx.toFixed(2)),
                                  markerWidthSpread:Number(markerWidthSpread.toFixed(2)),
                                  markerHeightSpread:Number(markerHeightSpread.toFixed(2)),
                                  parallelErrorDeg:Number(parallelErrorDeg.toFixed(2)),
                                  lengthSpreadMm:Number(lengthSpreadMm.toFixed(2))});
            if (widthSpreadPx > 0.1 || markerWidthSpread > 0.1 || markerHeightSpread > 0.1) {
              issues.push({type:'arrow-style-group-mismatch', group:id,
                           strokeWidthSpreadPx:Number(widthSpreadPx.toFixed(2)),
                           markerWidthSpread:Number(markerWidthSpread.toFixed(2)),
                           markerHeightSpread:Number(markerHeightSpread.toFixed(2))});
            }
            if (parallelErrorDeg > 0.5) {
              issues.push({type:'arrow-style-group-not-parallel', group:id,
                           parallelErrorDeg:Number(parallelErrorDeg.toFixed(2)), maximumDeg:0.5});
            }
            if (lengthSpreadMm > 0.3) {
              issues.push({type:'arrow-style-group-length-mismatch', group:id,
                           lengthSpreadMm:Number(lengthSpreadMm.toFixed(2)), maximumMm:0.3});
            }
          }

          const repeatGroups = new Map();
          for (const item of svg.querySelectorAll('[data-repeat-group]')) {
            const id = item.getAttribute('data-repeat-group');
            if (!repeatGroups.has(id)) repeatGroups.set(id, []);
            repeatGroups.get(id).push(item);
          }
          for (const [id, items] of repeatGroups) {
            if (items.length < 2) continue;
            const direction = items[0].getAttribute('data-repeat-direction') || 'horizontal';
            const rects = items.map(rectOf);
            const reference = rects[0];
            for (const rect of rects.slice(1)) {
              const crossAxisErrorPx = direction === 'horizontal'
                ? Math.max(Math.abs(rect.top-reference.top), Math.abs(rect.height-reference.height))
                : Math.max(Math.abs(rect.left-reference.left), Math.abs(rect.width-reference.width));
              if (crossAxisErrorPx / mm > 0.5) {
                issues.push({type:'repeat-group-misaligned', group:id, direction,
                             errorMm:Number((crossAxisErrorPx/mm).toFixed(2))});
              }
            }
            if (rects.length > 2) {
              const ordered = [...rects].sort((a, b) => direction === 'horizontal' ? a.left-b.left : a.top-b.top);
              const gaps = ordered.slice(1).map((rect, index) => direction === 'horizontal'
                ? rect.left-ordered[index].right : rect.top-ordered[index].bottom);
              const spread = Math.max(...gaps) - Math.min(...gaps);
              if (spread / mm > 0.5) {
                issues.push({type:'repeat-group-uneven-gap', group:id,
                             spreadMm:Number((spread/mm).toFixed(2))});
              }
            }
          }

          const alignGroups = new Map();
          for (const item of svg.querySelectorAll('[data-align-group]')) {
            const id = item.getAttribute('data-align-group');
            if (!alignGroups.has(id)) alignGroups.set(id, []);
            alignGroups.get(id).push(item);
          }
          for (const [id, items] of alignGroups) {
            if (items.length < 2) continue;
            const axis = items[0].getAttribute('data-align-axis') || 'x';
            const centers = items.map(item => {
              const rect = item.getBoundingClientRect();
              return axis === 'x' ? (rect.left+rect.right)/2 : (rect.top+rect.bottom)/2;
            });
            const spreadMm = (Math.max(...centers)-Math.min(...centers))/mm;
            semanticMetrics.push({alignGroup:id, axis, spreadMm:Number(spreadMm.toFixed(2))});
            if (spreadMm > 0.5) {
              issues.push({type:'optical-group-misaligned', group:id, axis,
                           spreadMm:Number(spreadMm.toFixed(2)), maximumMm:0.5});
            }
          }

          const stackGroups = new Map();
          for (const item of svg.querySelectorAll('[data-stack-group]')) {
            const id = item.getAttribute('data-stack-group');
            if (!stackGroups.has(id)) stackGroups.set(id, []);
            stackGroups.get(id).push(item);
          }
          for (const [id, items] of stackGroups) {
            if (items.length < 2) continue;
            const ordered = [...items].sort((a, b) =>
              Number(a.getAttribute('data-stack-order')) - Number(b.getAttribute('data-stack-order'))
            );
            const rects = ordered.map(rectOf);
            const centers = rects.map(rect => (rect.left + rect.right) / 2);
            const centerSpreadMm = (Math.max(...centers) - Math.min(...centers)) / mm;
            const gapsMm = rects.slice(1).map((rect, index) =>
              Number(((rect.top - rects[index].bottom) / mm).toFixed(2))
            );
            semanticMetrics.push({stackGroup:id,
                                  centerSpreadMm:Number(centerSpreadMm.toFixed(2)),
                                  gapsMm});
            if (centerSpreadMm > 0.5) {
              issues.push({type:'stack-group-off-center', group:id,
                           centerSpreadMm:Number(centerSpreadMm.toFixed(2)), maximumMm:0.5});
            }
            for (const gapMm of gapsMm) {
              if (gapMm < 1.5 || gapMm > 3.0) {
                issues.push({type:'stack-group-gap', group:id, gapMm,
                             allowedMm:[1.5, 3.0]});
              }
            }
          }

          const axisGapMin = 4.0;
          const axisGapMax = 6.0;
          for (const title of svg.querySelectorAll('[data-axis-title]')) {
            const orientation = title.getAttribute('data-axis-title');
            const axis = svg.querySelector(`[data-axis="${orientation}"]`);
            if (!axis) {
              issues.push({type:'missing-axis-for-title', orientation});
              continue;
            }
            const tr = title.getBoundingClientRect();
            const ar = axis.getBoundingClientRect();
            const gapPx = orientation === 'y' ? ar.left - tr.right : tr.top - ar.bottom;
            const gapMm = gapPx / mm;
            const metric = {orientation,
                            axisTitleGapMm:Number(gapMm.toFixed(2))};
            if (gapMm < axisGapMin || gapMm > axisGapMax) {
              issues.push({type:'axis-title-gap', orientation,
                           gapMm:Number(gapMm.toFixed(2)),
                           allowedMm:[axisGapMin, axisGapMax]});
            }

            const name = title.querySelector('[data-axis-part="name"]');
            const symbol = title.querySelector('[data-axis-part="symbol"]');
            if (name && symbol) {
              const nr = name.getBoundingClientRect();
              const sr = symbol.getBoundingClientRect();
              metric.nameAdvance = Number(name.getComputedTextLength().toFixed(2));
              metric.symbolAdvance = Number(symbol.getComputedTextLength().toFixed(2));
              const tokenGapPx = orientation === 'y' ? nr.top - sr.bottom : sr.left - nr.right;
              const tokenGapMm = tokenGapPx / mm;
              metric.tokenGapMm = Number(tokenGapMm.toFixed(2));
              if (tokenGapMm < 0.8 || tokenGapMm > 1.2) {
                issues.push({type:'axis-token-gap', orientation,
                             gapMm:Number(tokenGapMm.toFixed(2)),
                             allowedMm:[0.8, 1.2]});
              }
            }
            semanticMetrics.push(metric);
          }

          const style = getComputedStyle(texts[0]);
          return {
            title: svg.querySelector('title')?.textContent || '',
            textCount: texts.length,
            obstacleCount: obstacles.length,
            boundaryCount: boundaryRects.length,
            arrowCount: arrows.length,
            anchorCount: anchorMap.size,
            fontFamily: style?.fontFamily || '',
            root: {width:root.width, height:root.height},
            semanticMetrics,
            issues
          };
        }"""
    )


def render_exports(svg_path: Path, export_pdf: bool) -> dict[str, Any]:
    svg_bytes = svg_path.read_bytes()
    stem = svg_path.stem
    png_path = svg_path.with_name(f"{stem}-预览.png")

    width_mm = svg_width_mm(svg_path.read_text(encoding="utf-8"))
    output_width = round(width_mm / 25.4 * PREVIEW_DPI)
    cairosvg.svg2png(bytestring=svg_bytes, write_to=str(png_path), output_width=output_width)
    pdf_path = svg_path.with_suffix(".pdf")
    if export_pdf:
        cairosvg.svg2pdf(bytestring=svg_bytes, write_to=str(pdf_path))

    with Image.open(png_path) as image:
        grayscale = image.convert("L")
        stats = ImageStat.Stat(grayscale)
        return {
            "png": png_path.name,
            "pdf": pdf_path.name if export_pdf else None,
            "pixels": [image.width, image.height],
            "dpi_target": PREVIEW_DPI,
            "grayscale_stddev": round(stats.stddev[0], 2),
        }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--audit-only", action="store_true", help="inspect without writing exports or reports")
    parser.add_argument("--pdf", action="store_true", help="also export vector PDF; PNG is always written")
    parser.add_argument("--pattern", default="*.svg", help="SVG filename glob, for example '图3-*.svg'")
    args = parser.parse_args()
    directory = args.directory.resolve()
    svg_paths = sorted(directory.glob(args.pattern))
    if not svg_paths:
        raise SystemExit(f"No SVG figures found in {directory}")

    browser = await launch(
        executablePath=_chromium_path(),
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"],
    )
    page = await browser.newPage()
    results = []
    try:
        for svg_path in svg_paths:
            inspection = await inspect_svg(page, svg_path)
            inspection["issues"].extend(audit_svg_fonts(svg_path))
            export = {} if args.audit_only else render_exports(svg_path, args.pdf)
            results.append({"file": svg_path.name, **inspection, "export": export})
    finally:
        await browser.close()

    issue_count = sum(len(result["issues"]) for result in results)
    if args.audit_only:
        summary = {
            "status": "PASS" if issue_count == 0 else "FAIL",
            "issue_count": issue_count,
            "figures": [
                {"file": result["file"], "issues": result["issues"]}
                for result in results
            ],
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if issue_count == 0 else 1
    report = {
        "standard": "academic-figure-workflow/references/visual-spec.md",
        "status": "PASS" if issue_count == 0 else "FAIL",
        "issue_count": issue_count,
        "figures": results,
    }
    (directory / "QA报告.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# Academic figure QA report",
        "",
        f"- 自动验收：**{report['status']}**",
        f"- 自动 QA 问题：**{issue_count}**",
        f"- 最终预览导出：{PREVIEW_DPI} dpi",
        "- 字体测量：等待 `document.fonts.ready` 后使用浏览器最终布局",
        "",
        "| 文件 | 文字 | 箭头 | 锚点 | 边界框 | 预览像素 | 问题 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        px = "×".join(map(str, result["export"]["pixels"]))
        lines.append(
            f"| {result['file']} | {result['textCount']} | {result['arrowCount']} | {result['anchorCount']} | {result['boundaryCount']} | {px} | {len(result['issues'])} |"
        )
    axis_metrics = [
        metric
        for result in results
        for metric in result.get("semanticMetrics", [])
        if "orientation" in metric
    ]
    if axis_metrics:
        lines.extend([
            "",
            "## 坐标轴标题间距",
            "",
            "| 方向 | 标题—轴线 | 名称—符号 | 规范 |",
            "|---|---:|---:|---|",
        ])
        for metric in axis_metrics:
            lines.append(
                f"| {metric['orientation']} | {metric['axisTitleGapMm']:.2f} mm | "
                f"{metric.get('tokenGapMm', float('nan')):.2f} mm | "
                "4–6 mm；0.8–1.2 mm |"
            )
    arrow_metrics = [
        metric
        for result in results
        for metric in result.get("semanticMetrics", [])
        if "arrowTarget" in metric
    ]
    if arrow_metrics:
        max_alignment = max(metric["alignmentErrorMm"] for metric in arrow_metrics)
        min_gap = min(metric["terminalGapMm"] for metric in arrow_metrics)
        max_gap = max(metric["terminalGapMm"] for metric in arrow_metrics)
        lines.extend([
            "",
            "## 箭头—目标几何关系",
            "",
            f"- 受约束箭头：{len(arrow_metrics)}",
            f"- 最大中心线偏差：{max_alignment:.2f} mm（上限 0.50 mm）",
            f"- 终点间隙范围：{min_gap:.2f}–{max_gap:.2f} mm（允许 0.80–2.00 mm）",
        ])
    source_metrics = [
        metric
        for result in results
        for metric in result.get("semanticMetrics", [])
        if "arrowSource" in metric
    ]
    if source_metrics:
        max_source_alignment = max(metric["alignmentErrorMm"] for metric in source_metrics)
        min_source_gap = min(metric["terminalGapMm"] for metric in source_metrics)
        max_source_gap = max(metric["terminalGapMm"] for metric in source_metrics)
        lines.extend([
            f"- 受约束箭头起点：{len(source_metrics)}",
            f"- 起点最大中心线偏差：{max_source_alignment:.2f} mm（上限 0.50 mm）",
            f"- 起点间隙范围：{min_source_gap:.2f}–{max_source_gap:.2f} mm",
            "- 连续引线的 touch 起点允许 −0.20–0.20 mm；独立箭头允许 0.80–2.00 mm。",
        ])
    label_metrics = [
        metric
        for result in results
        for metric in result.get("semanticMetrics", [])
        if "arrowLabel" in metric
    ]
    if label_metrics:
        min_label_gap = min(metric["distanceMm"] for metric in label_metrics)
        max_label_gap = max(metric["distanceMm"] for metric in label_metrics)
        lines.extend([
            "",
            "## 箭头—标签归属",
            "",
            f"- 绑定标签：{len(label_metrics)}",
            f"- 标签到所属箭头的最近距离：{min_label_gap:.2f}–{max_label_gap:.2f} mm（允许 1.00–4.00 mm）",
        ])
    align_metrics = [
        metric
        for result in results
        for metric in result.get("semanticMetrics", [])
        if "alignGroup" in metric
    ]
    if align_metrics:
        max_align_spread = max(metric["spreadMm"] for metric in align_metrics)
        lines.extend([
            "",
            "## 光学对齐组",
            "",
            f"- 对齐组：{len(align_metrics)}",
            f"- 最大中心轴离散：{max_align_spread:.2f} mm（上限 0.50 mm）",
        ])
    stack_metrics = [
        metric
        for result in results
        for metric in result.get("semanticMetrics", [])
        if "stackGroup" in metric
    ]
    if stack_metrics:
        max_stack_spread = max(metric["centerSpreadMm"] for metric in stack_metrics)
        all_stack_gaps = [gap for metric in stack_metrics for gap in metric["gapsMm"]]
        lines.extend([
            "",
            "## 纵向信息组",
            "",
            f"- 信息组：{len(stack_metrics)}",
            f"- 最大中心轴离散：{max_stack_spread:.2f} mm（上限 0.50 mm）",
            f"- 相邻元素间距：{min(all_stack_gaps):.2f}–{max(all_stack_gaps):.2f} mm（允许 1.50–3.00 mm）",
        ])
    orthogonal_metrics = [
        metric
        for result in results
        for metric in result.get("semanticMetrics", [])
        if metric.get("orthogonalRoute")
    ]
    if orthogonal_metrics:
        max_first_deviation = max(metric["firstLegDeviationMm"] for metric in orthogonal_metrics)
        max_second_deviation = max(metric["secondLegDeviationMm"] for metric in orthogonal_metrics)
        lines.extend([
            "",
            "## 正交引线",
            "",
            f"- 正交引线：{len(orthogonal_metrics)}",
            f"- 起始垂直段偏差：{max_first_deviation:.2f} mm（上限 0.20 mm）",
            f"- 末端水平段偏差：{max_second_deviation:.2f} mm（上限 0.20 mm）",
        ])
    axis_aligned_metrics = [
        metric
        for result in results
        for metric in result.get("semanticMetrics", [])
        if metric.get("axisAlignedRoute")
    ]
    if axis_aligned_metrics:
        max_axis_deviation = max(metric["axisDeviationMm"] for metric in axis_aligned_metrics)
        lines.extend([
            "",
            "## 轴向引线",
            "",
            f"- 轴向引线：{len(axis_aligned_metrics)}",
            f"- 轴线偏差：{max_axis_deviation:.2f} mm（上限 0.20 mm）",
        ])
    radial_metrics = [
        metric
        for result in results
        for metric in result.get("semanticMetrics", [])
        if metric.get("radialDiagonalRoute")
    ]
    if radial_metrics:
        max_radial_deviation = max(metric["radialDeviationMm"] for metric in radial_metrics)
        lines.extend([
            "",
            "## 斜向径向引线",
            "",
            f"- 径向引线：{len(radial_metrics)}",
            f"- 直线到标记视觉中心的偏差：{max_radial_deviation:.2f} mm（上限 0.20 mm）",
        ])
    style_group_metrics = [
        metric
        for result in results
        for metric in result.get("semanticMetrics", [])
        if "arrowStyleGroup" in metric
    ]
    if style_group_metrics:
        lines.extend(["", "## 同构箭头组", ""])
        for metric in style_group_metrics:
            lines.append(
                f"- `{metric['arrowStyleGroup']}`：线宽离散 {metric['strokeWidthSpreadPx']:.2f} px，"
                f"箭头尺寸离散 {max(metric['markerWidthSpread'], metric['markerHeightSpread']):.2f}，"
                f"平行角度误差 {metric['parallelErrorDeg']:.2f}°，"
                f"长度离散 {metric['lengthSpreadMm']:.2f} mm"
            )
    typography_metrics = [
        metric
        for result in results
        for metric in result.get("semanticMetrics", [])
        if "typographyGroup" in metric
    ]
    if typography_metrics:
        lines.extend(["", "## 同级字号组", ""])
        for metric in typography_metrics:
            lines.append(
                f"- `{metric['typographyGroup']}`：{metric['itemCount']} 项，"
                f"字号离散 {metric['sizeSpreadPx']:.2f} px，"
                f"字重 {', '.join(metric['weights'])}"
            )
    lines.extend(["", "## 未通过项", ""])
    if issue_count:
        for result in results:
            for issue in result["issues"]:
                lines.append(f"- `{result['file']}`：`{issue['type']}` — {issue}")
    else:
        lines.append("无。")
    lines.extend([
        "",
        "## 人工检查",
        "",
        "自动检查通过后仍需逐张查看最终尺寸预览，确认信息层级、阅读顺序、灰度可辨性和 WPS 插入效果。",
    ])
    (directory / "QA报告.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "issue_count": issue_count}, ensure_ascii=False))
    return 0 if issue_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
