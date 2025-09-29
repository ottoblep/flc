{
  description = "Foxhole Logistics Calculator";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }: let
    system = "x86_64-linux";
    pkgs = nixpkgs.legacyPackages.${system};
  in {
    packages.${system}.default = pkgs.python3Packages.buildPythonApplication {
      pname = "flc";
      version = "0.1.0";
      src = ./.;
      format = "other";
      buildPhase = ":";
      installPhase = ''
        mkdir -p $out/bin
        cp process_tsv.py $out/bin/process_tsv
        chmod +x $out/bin/process_tsv
      '';
      propagatedBuildInputs = [ pkgs.python3Packages.pandas ];
    };

    apps.${system}.default = {
      type = "app";
      program = "${self.packages.${system}.default}/bin/process_tsv";
    };
  };
}