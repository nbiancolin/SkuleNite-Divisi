import { useState, useEffect } from "react";
import {
  Text,
  Notification,
  TextInput,
  Box,
  SegmentedControl,
  Group,
  Alert,
  Loader,
} from "@mantine/core";
import '../fonts.css'

// Define the props interface
interface ScoreTitlePreviewProps {
  selectedStyle: string;
  setSelectedStyle: (style: string) => void;
  title: string;
  subtitle: string;
  composer: string;
  arranger: string|null;
  showTitle: string|null;
  mvtNo: string;
  pieceNumber: number|null;
}

export function ScoreTitlePreview({
  selectedStyle,
  setSelectedStyle,
  title,
  subtitle,
  composer,
  arranger, 
  mvtNo,
  showTitle,
  pieceNumber
}: ScoreTitlePreviewProps) {
  const previewStyleOptions = {
    "broadway": {
      "title": {
        margin: '0 0 8px 0',
        textDecoration: 'underline',
        fontFamily: "Palatino, sans-serif",
      },
      "subtitle": {
        margin: '0', 
        fontWeight: 'normal',
        fontFamily: "Palatino, sans-serif",
      },
      "composer": {
        margin: '0', 
        fontWeight: 'normal',
        fontFamily: "Palatino, sans-serif",
      },
      "arranger": {
        margin: '0', 
        fontWeight: 'normal',
        fontFamily: "Palatino, sans-serif",
        fontStyle: "italic",
      },
      "mvtNo": {
        margin: 0, 
        fontSize: '1.5rem',
        fontFamily: "Palatino, sans-serif",
      },
      "showTitle": {
        margin: '0', 
        fontWeight: 'normal',
        fontFamily: "Palatino, sans-serif",
        textDecoration: 'underline',
        whiteSpace: "nowrap",
      },
      "partName": {
        fontFamily: "Palatino, sans-serif",
      }
    },
    "classical": {
      "title": {
        margin: '0 0 8px 0',
        textDecoration: 'underline',
        fontFamily: "Palatino, sans-serif",
      },
      "subtitle": {
        margin: '0', 
        fontWeight: 'normal',
        fontFamily: "Palatino, sans-serif",
      },
      "composer": {
        margin: '0', 
        fontWeight: 'normal',
        fontFamily: "Palatino, sans-serif",
      },
      "arranger": {
        margin: '0', 
        fontWeight: 'normal',
        fontFamily: "Palatino, sans-serif",
        fontStyle: "italic",
      },
      "partName": {
        fontFamily: "Palatino, sans-serif",
      }
    },
    "jazz": {
      "title": {
        margin: '0 0 8px 0',
        textDecoration: 'underline',
        fontFamily: "Inkpen2, sans-serif",
      },
      "subtitle": {
        margin: '0', 
        fontWeight: 'normal',
        fontFamily: "Inkpen2, sans-serif",
      },
      "composer": {
        margin: '0', 
        fontWeight: 'normal',
        fontFamily: "Inkpen2, sans-serif",
      },
      "arranger": {
        margin: '0', 
        fontWeight: 'normal',
        fontFamily: "Inkpen2, sans-serif",
      },
      "partName": {
        fontFamily: "Inkpen2, sans-serif",
      }
    },
  }

  return (
    <>
      <SegmentedControl 
        fullWidth
        size="md"
        mt="md"
        value={selectedStyle}
        onChange={setSelectedStyle}
        data={[
          {label: "Broadway", value: "broadway"},
          {label: "Jazz", value: "jazz"},
          {label: "Classical", value: "classical"},
        ]}
      />
      <Box
        mt="xl"
        mb="xl"
        p="md"
        style={{
            border: '1px solid #dee2e6',
            borderRadius: '8px',
            width: '100%',
            position: 'relative'
        }}
        >
        <Text size="sm" mb="md" style={{ color: '#666' }}>
            Title Preview:
        </Text>
        {title && (
          <Box
            style={{
              display: "flex",
              alignItems: "center", // vertical alignment
              justifyContent: "space-between", // push left/right
              marginBottom: "1rem"
            }}
          >
            <h3 style={previewStyleOptions[selectedStyle].partName}>
              Conductor Score
            </h3>

            {(mvtNo || pieceNumber || showTitle) && selectedStyle === "broadway" && (
              <Box style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                {showTitle && (
                  <span style={previewStyleOptions[selectedStyle].showTitle}>
                    {showTitle}
                  </span>
                )}
                <Box
                  style={{
                    border: "1px solid black",
                    padding: "0.25rem 0.75rem",
                  }}
                >
                  <h1 style={previewStyleOptions[selectedStyle].mvtNo}>
                    {mvtNo || pieceNumber}
                  </h1>
                </Box>
              </Box>
            )}
          </Box>
        )}
        
        <div style={{ textAlign: 'center' }}>
            {title && (
            <h1 style={previewStyleOptions[selectedStyle].title}>
                {title}
            </h1>
            )}
            
            {subtitle && (
            <h3 style={previewStyleOptions[selectedStyle].subtitle}>
                {subtitle}
            </h3>
            )}
        </div>
        <div style={{textAlign: 'right'}}>
            {composer && (
            <h4 style={previewStyleOptions[selectedStyle].composer}>
                {composer}
            </h4>
            )}
            {arranger && (
              <h4 style={previewStyleOptions[selectedStyle].arranger}> 
                arr. {arranger}  
              </h4>
            )}
        </div>
        
        {!title && !subtitle && !mvtNo && (
            <Text style={{ color: '#999', fontStyle: 'italic', textAlign: 'center' }}>
            Fill in the fields above to see a preview of your arrangement header
            </Text>
        )}
        </Box>
      </>
  )
}