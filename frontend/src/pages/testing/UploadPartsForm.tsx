// UploadPartsForm.tsx
import { useState, useEffect } from 'react';
import { FileInput, Radio, Button, Container, Group, Text, Center, Loader } from '@mantine/core';
import axios from 'axios';
import { useLocation } from 'react-router-dom';

interface Arrangements {
  id: number;
  ensemble_name: string;
  title: string;
  subtitle: string;
  mvt_no: string;
  latest_version: string;
}


function useQuery() {
  return new URLSearchParams(useLocation().search);
}

export function UploadPartsForm() {
  const [files, setFiles] = useState<File[]>([]);
  const [versionType, setVersionType] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState<boolean>(true);
  const [arrangements, setArrangements] = useState<Arrangements[]>([])
  const query = useQuery();

  const id = query.get('id');

  useEffect(() => {
    const fetchEnsembles = async () => {
      if (!id) return; // skip if no id

      try {
        const response = await axios.get<Arrangements[]>(`http://localhost:8000/api/arrangements/?id=${id}`);
        setArrangements(response.data);
      } catch (error) {
        console.error('Failed to fetch ensembles:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchEnsembles();
  }, [id]);

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
  if (loading) {
    return (
      <Center h="100vh">
        <Loader size="lg" />
      </Center>
    );
    }

  return (
    <Container py="md">
      <h2>Upload new Version for <em>{arrangements[0].title}</em></h2>
      <FileInput
        mt="md"
        label="Select PDF Parts"
        placeholder="Upload one or more PDFs"
        multiple
        accept="application/pdf"
        value={files}
        onChange={(f: any) => setFiles(Array.isArray(f) ? f : [f])}
      />
      <Radio.Group value={versionType} onChange={setVersionType} name="pickVersionLabel" label="Select Release Type" withAsterisk>
        <Radio value="major" label="Major (v1.0.0)" />
        <Radio value="minor" label="Minor (v1.1.0)" />
        <Radio value="patch" label="Patch (v1.0.1)" />
      </Radio.Group>
      

      <Group justify="right" mt="md">
        <Button onClick={handleUpload}>Upload</Button>
      </Group>
      {message && <Text mt="md">{message}</Text>}
    </Container>
  );
}
