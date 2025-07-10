let
  pkgs = import <nixpkgs> {
    config = {
      allowUnfree = true;
      cudaSupport = true;
    };
  };  


in pkgs.mkShell rec {
  nativeBuildInputs = with pkgs.buildPackages; [  
    nodejs
    python311Full 

  ];

  shellHook = ''
    python -m venv .venv
    source .venv/bin/activate
    export CUDA_PATH=${pkgs.cudatoolkit}

    pip install -r requirements.txt

    export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath nativeBuildInputs}:$LD_LIBRARY_PATH"
    export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib.outPath}/lib:$LD_LIBRARY_PATH"
    export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [pkgs.stdenv.cc.cc]}:'/run/opengl-driver/lib':$LD_LIBRARY_PATH"
    export LD_LIBRARY_PATH="${pkgs.libGL}/lib/:$LD_LIBRARY_PATH"
    export LD_LIBRARY_PATH="${pkgs.glibc}/lib:$LD_LIBRARY_PATH"
  '';
}
