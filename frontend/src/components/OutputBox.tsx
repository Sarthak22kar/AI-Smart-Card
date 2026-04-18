interface Props {
    output: string;
  }
  
  function OutputBox({ output }: Props) {
    return (
      <div style={{ marginTop: "20px", whiteSpace: "pre-wrap" }}>
        {output}
      </div>
    );
  }
  
  export default OutputBox;