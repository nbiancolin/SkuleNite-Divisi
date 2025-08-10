import { useState } from "react";
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Button,
  Title,
  Text,
  Notification,
  TextInput,
  
} from "@mantine/core";
import { X, } from "lucide-react";
import { apiService } from '../../services/apiService';
import { IconArrowLeft } from '@tabler/icons-react';
import { ScoreTitlePreview } from "../../components/ScoreTitlePreview";
import type { PreviewStyleName } from "../../components/ScoreTitlePreview";


export default function CreateEnsemblePage() {
  const [error, setError] = useState<string | null>(null);
  const [ensembleName, setEnsebleName] = useState<string>("My First Ensemble")
  const [selectedStyle, setSelectedStyle] = useState<PreviewStyleName>("broadway")

  const navigate = useNavigate();
  const createEnsemble = async () => {

    try {
      const data = await apiService.createEnsemble(ensembleName, selectedStyle)
      
      window.location.href = `/app/ensembles/${data.slug}/arrangements`;
    } catch (err: any) {
      console.error("Formatting error:", err);
      setError(err.message || "Create Ensemble failed."); 
    } 
  };

  return (
    <Container size="sm" py="xl">
      {/* TODO: Remove this when adding users */}
      <Button
        variant="subtle"
        leftSection={<IconArrowLeft size={16} />}
        onClick={() => { navigate('/app/ensembles'); }}
      >
        Back to Ensembles
      </Button>
      <Title ta="center" mb="xl">
        Get started with Divisi
      </Title>
      <Text>Enter the name of your ensemble.</Text>
      <Text>Note that ensemble names are unique.</Text>
      <TextInput
        label="Ensemble Name"
        value={ensembleName}
        onChange={(e) => setEnsebleName(e.currentTarget.value)}
        mt="md"
      />

      <Text mt="md"> Default Style for Arrangements in this ensemble:</Text>

      <ScoreTitlePreview
        selectedStyle={selectedStyle}
        setSelectedStyle={setSelectedStyle}
        title={"Title"}
        subtitle={"subtitle"}
        ensemble={ensembleName}
        composer={"composer"}
        showTitle={"My Broadway Show"}
        arranger={"arranger"}
        mvtNo={"0-0"}
        pieceNumber={0}
      />

      <Button
        onClick={createEnsemble}
        fullWidth
        mt="md"
      >
        Create Ensemble
      </Button>

      {error && (
        <Notification
          mt="xl"
          icon={<X size={18} />}
          color="red"
          title="Error"
          onClose={() => setError(null)}
        >
          {error}
        </Notification>
      )}
    </Container>
  );
}
