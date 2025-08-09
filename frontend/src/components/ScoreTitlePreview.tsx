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
  mvtNo: string;
  pieceNumber: number|null;
}

export function ScoreTitlePreview({
  selectedStyle,
  setSelectedStyle,
  title,
  subtitle,
  composer,
  mvtNo,
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
      "mvtNo": {
        margin: 0, 
        fontSize: '1.5rem',
        fontFamily: "Palatino, sans-serif",
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
      "mvtNo": {
        margin: 0, 
        fontSize: '1.5rem',
        fontFamily: "Palatino, sans-serif",
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
      "mvtNo": {
        margin: 0, 
        fontSize: '1.5rem',
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
            <h3 style={previewStyleOptions[selectedStyle].partName}> Conductor Score</h3>
        )}
        
        
        {(mvtNo || pieceNumber) && (selectedStyle == "broadway") && (
            <Box
            style={{
                position: 'absolute',
                top: '16px',
                right: '16px'
            }}
            bd="2px solid "
            p="sm"
            >
            <h1 style={previewStyleOptions[selectedStyle].mvtNo}>
                {mvtNo || pieceNumber}
            </h1>
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