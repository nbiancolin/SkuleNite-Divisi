// UploadPartsForm.tsx
import { useState, version } from 'react';
import { FileInput, Radio, Button, Box, Group, Text } from '@mantine/core';
import axios from 'axios';
import { useLocation } from 'react-router-dom';

function useQuery() {
  return new URLSearchParams(useLocation().search);
}

export function UploadPartsForm() {
  const [files, setFiles] = useState<File[]>([]);
  const [versionType, setVersionType] = useState('');
  const [message, setMessage] = useState('');
  const query = useQuery();

  const id = query.get('id');

  const handleUpload = async () => {
    console.log(id)
    console.log(versionType)
    console.log(files.length)
    if (!id || !versionType || files.length === 0) {
      setMessage('All fields are required');
      return;
    }

    const formData = new FormData();
    formData.append('arrangement_id', id);
    formData.append('version_type', versionType);
    formData.append('is_latest', 'true')
    files.forEach((file) => formData.append('files', file));
    
    console.log("here1")
    try {
      const response = await axios.post('http://localhost:8000/api/upload-parts/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setMessage(response.data.message || 'Upload successful');
    } catch (error: any) {
      setMessage('Upload failed: ' + (error.response?.data?.detail || ''));
    }
  };

  return (
    <Box maw={500} mx="auto" mt="xl">
      {/* <TextInput
        mt="md"
        label="Version Label"
        placeholder="e.g. 1.0.0"
        value={versionLabel}
        onChange={(e) => setVersionLabel(e.currentTarget.value)}
        required
      /> */}
      <FileInput
        mt="md"
        label="Select PDF Parts"
        placeholder="Upload one or more PDFs"
        multiple
        accept="application/pdf"
        value={files}
        onChange={(f: any) => setFiles(Array.isArray(f) ? f : [f])}
      />
      <Radio.Group value={versionType} onChange={setVersionType} name="pickVersionLabel" label="Select Release Type" description="description" withAsterisk>
        <Radio value="major" label="Major (v1.0.0)" />
        <Radio value="minor" label="Minor (v1.1.0)" />
        <Radio value="patch" label="Patch (v1.0.1)" />
      </Radio.Group>
      

      <Group position="right" mt="md">
        <Button onClick={handleUpload}>Upload</Button>
      </Group>
      {message && <Text mt="md">{message}</Text>}
    </Box>
  );
}
